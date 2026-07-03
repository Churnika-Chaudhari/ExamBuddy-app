import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import BackgroundTasks

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.enums import AnalysisStatus, ProcessingStatus
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.stats_repository import StatsRepository
from app.services.ai.ai_service import AIService
from app.services.mappers import map_document_response
from app.services.subject_service import SubjectService
from app.services.pipeline.notes_pipeline import NotesPipeline
from app.services.quiz_service import _topics_from_analysis_doc

logger = logging.getLogger(__name__)
settings = get_settings()


class AnalysisService:
    def __init__(
        self,
        analysis_repo: AnalysisRepository,
        document_repo: DocumentRepository,
        stats_repo: StatsRepository,
        ai_service: AIService | None = None,
        subject_service: SubjectService | None = None,
    ) -> None:
        self.analysis_repo = analysis_repo
        self.document_repo = document_repo
        self.stats_repo = stats_repo
        self.ai_service = ai_service or AIService()
        self.subject_service = subject_service
        self.notes_pipeline = NotesPipeline()

    async def create_analysis(
        self,
        user_id: str,
        document_ids: list[str],
        *,
        subject: str | None,
        title: str | None,
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any]:
        if len(document_ids) > settings.max_pyq_documents_per_analysis:
            raise ValidationAppError(
                f"Maximum {settings.max_pyq_documents_per_analysis} documents allowed per analysis"
            )

        documents = await self.document_repo.get_many_by_ids(document_ids, user_id)
        if len(documents) != len(document_ids):
            raise NotFoundError("One or more documents not found")

        not_ready = [doc for doc in documents if doc.get("status") != ProcessingStatus.READY]
        if not_ready:
            raise ValidationAppError(
                "All documents must be processed before analysis",
                details=[{"id": str(doc["_id"]), "status": doc.get("status")} for doc in not_ready],
            )

        now = datetime.now(UTC)
        analysis = await self.analysis_repo.create(
            {
                "user_id": self.analysis_repo.to_object_id(user_id),
                "document_ids": [doc["_id"] for doc in documents],
                "subject": subject or documents[0].get("subject"),
                "title": title or f"PYQ Analysis - {now.strftime('%Y-%m-%d %H:%M')}",
                "status": AnalysisStatus.PROCESSING,
                "repeated_questions": [],
                "topic_frequency": {},
                "important_topics": [],
                "topic_table": [],
                "academic_topic_table": [],
                "topic_frequency_table": [],
                "high_priority_topics": [],
                "medium_priority_topics": [],
                "low_priority_topics": [],
                "predicted_important_topics": [],
                "most_important_topics": [],
                "frequently_asked_topics": [],
                "rarely_asked_topics": [],
                "topic_groups": [],
                "syllabus_topics": [],
                "exam_patterns": [],
                "summary": None,
                "ai_metadata": None,
                "error_message": None,
                "created_at": now,
                "completed_at": None,
            }
        )

        await self.stats_repo.increment_field(user_id, "analyses_count")
        background_tasks.add_task(
            self._run_analysis,
            str(analysis["_id"]),
            user_id,
            documents,
        )

        return self._map_analysis(analysis)

    async def _run_analysis(
        self,
        analysis_id: str,
        user_id: str,
        documents: list[dict[str, Any]],
    ) -> None:
        try:
            combined_text = "\n\n---\n\n".join(
                f"Document: {doc.get('title', 'Untitled')}\n{doc.get('extracted_text', '')}"
                for doc in documents
                if doc.get("extracted_text")
            )
            if not combined_text.strip():
                raise ValidationAppError("No extractable text found in selected documents")

            subject = documents[0].get("subject")
            pipeline_result = self.notes_pipeline.run(
                combined_text,
                subject=subject,
                num_documents=len(documents),
            )
            cleaned_text = pipeline_result.cleaned_text
            local_analysis = pipeline_result.topic_analysis

            result, metadata = await self.ai_service.analyze_pyq(
                cleaned_text,
                subject,
                num_documents=len(documents),
                local_topics=local_analysis,
            )
            result = self.notes_pipeline.merge_ai_analysis(local_analysis, result)
            metadata["pipeline"] = {
                "lines_removed": pipeline_result.preprocess_stats.lines_removed,
                "questions_parsed": len(pipeline_result.question_lines),
                "topics_extracted": len(result.get("topic_table") or []),
            }

            await self.analysis_repo.update(
                analysis_id,
                {
                    "status": AnalysisStatus.COMPLETED,
                    "repeated_questions": result.get("repeated_questions", []),
                    "topic_frequency": result.get("topic_frequency", {}),
                    "important_topics": result.get("important_topics", []),
                    "topic_table": result.get("topic_table", []),
                    "academic_topic_table": result.get("academic_topic_table", []),
                    "topic_frequency_table": result.get("topic_frequency_table", []),
                    "high_priority_topics": result.get("high_priority_topics", []),
                    "medium_priority_topics": result.get("medium_priority_topics", []),
                    "low_priority_topics": result.get("low_priority_topics", []),
                    "predicted_important_topics": result.get("predicted_important_topics", []),
                    "most_important_topics": result.get("most_important_topics", []),
                    "frequently_asked_topics": result.get("frequently_asked_topics", []),
                    "rarely_asked_topics": result.get("rarely_asked_topics", []),
                    "topic_groups": result.get("topic_groups", []),
                    "syllabus_topics": result.get("syllabus_topics", []),
                    "exam_patterns": result.get("exam_patterns", []),
                    "summary": result.get("summary"),
                    "ai_metadata": metadata,
                    "error_message": None,
                    "completed_at": datetime.now(UTC),
                },
            )
            await self.stats_repo.add_activity(
                user_id,
                {
                    "type": "pyq_analysis",
                    "ref_id": analysis_id,
                    "title": "PYQ Analysis completed",
                    "timestamp": datetime.now(UTC),
                },
            )
            if self.subject_service and subject:
                topic_count = len(_topics_from_analysis_doc(result))
                await self.subject_service.on_analysis_completed(user_id, subject, topic_count)
        except Exception as exc:
            logger.error("Analysis failed for %s: %s", analysis_id, exc)
            await self.analysis_repo.update(
                analysis_id,
                {
                    "status": AnalysisStatus.FAILED,
                    "error_message": str(exc),
                    "completed_at": datetime.now(UTC),
                },
            )

    async def list_analyses(self, user_id: str, *, page: int, limit: int) -> tuple[list[dict[str, Any]], int]:
        skip = (page - 1) * limit
        analyses = await self.analysis_repo.list_by_user(user_id, skip=skip, limit=limit)
        total = await self.analysis_repo.count_by_user(user_id)
        return [self._map_analysis(a) for a in analyses], total

    async def get_analysis(self, analysis_id: str, user_id: str) -> dict[str, Any]:
        analysis = await self.analysis_repo.get_by_id_and_user(analysis_id, user_id)
        if not analysis:
            raise NotFoundError("Analysis not found")
        return self._map_analysis(analysis)

    async def get_analysis_status(self, analysis_id: str, user_id: str) -> dict[str, Any]:
        analysis = await self.get_analysis(analysis_id, user_id)
        return {
            "id": analysis["id"],
            "status": analysis["status"],
            "error_message": analysis.get("error_message"),
        }

    async def delete_analysis(self, analysis_id: str, user_id: str) -> None:
        deleted = await self.analysis_repo.delete(analysis_id, user_id)
        if not deleted:
            raise NotFoundError("Analysis not found")
        await self.stats_repo.increment_field(user_id, "analyses_count", -1)

    def _map_analysis(self, analysis: dict[str, Any]) -> dict[str, Any]:
        mapped = map_document_response(analysis)
        mapped["document_ids"] = [str(doc_id) for doc_id in analysis.get("document_ids", [])]
        return mapped
