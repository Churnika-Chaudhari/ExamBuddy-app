from datetime import UTC, datetime
from typing import Any

import logging

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.enums import NoteSourceType, NoteType
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.generated_notes_repository import (
    GeneratedNotesRepository,
    normalize_topic_key,
)
from app.repositories.notes_repository import NotesRepository
from app.repositories.stats_repository import StatsRepository
from app.services.ai.ai_service import AIService
from app.services.ai.prompts import PROMPT_VERSION
from app.services.generated_note_mapper import map_generated_note
from app.services.pipeline.notes_pipeline import NotesPipeline
from app.services.mappers import map_document_response
from app.services.rag.retriever import DocumentRetriever
from app.utils.pdf_generator import generate_note_pdf_bytes
from app.utils.topic_extractor import filter_topics

logger = logging.getLogger(__name__)


def _topics_from_analysis(analysis: dict[str, Any], topics: list[str]) -> list[str]:
    if topics:
        return filter_topics(topics)
    if analysis.get("important_topics"):
        extracted = [t.get("topic", "") for t in analysis["important_topics"] if t.get("topic")]
        filtered = filter_topics(extracted)
        if filtered:
            return filtered
    if analysis.get("topic_frequency"):
        filtered = filter_topics(list(analysis["topic_frequency"].keys()))
        if filtered:
            return filtered[:15]
    return ["General Exam Topics"]


class NotesService:
    def __init__(
        self,
        notes_repo: NotesRepository,
        analysis_repo: AnalysisRepository,
        document_repo: DocumentRepository,
        stats_repo: StatsRepository,
        generated_notes_repo: GeneratedNotesRepository,
        ai_service: AIService | None = None,
    ) -> None:
        self.notes_repo = notes_repo
        self.analysis_repo = analysis_repo
        self.document_repo = document_repo
        self.stats_repo = stats_repo
        self.generated_notes_repo = generated_notes_repo
        self.ai_service = ai_service or AIService()
        self.rag_retriever = DocumentRetriever(document_repo)
        self.notes_pipeline = NotesPipeline()

    def _build_analysis_context(self, analysis: dict[str, Any]) -> str:
        context = analysis.get("summary") or ""
        if analysis.get("high_priority_topics"):
            context += "\nHigh priority topics:\n" + str(analysis["high_priority_topics"])
        if analysis.get("predicted_important_topics"):
            context += "\nPredicted important topics:\n" + str(
                analysis["predicted_important_topics"][:10]
            )
        if analysis.get("important_topics"):
            context += "\nImportant topics:\n" + str(analysis["important_topics"])
        if analysis.get("topic_frequency_table"):
            context += "\nTopic frequency:\n" + str(analysis["topic_frequency_table"][:15])
        return context

    async def generate_topic_note(
        self,
        user_id: str,
        topic: str,
        *,
        analysis_id: str | None = None,
        subject: str | None = None,
        unit: str | None = None,
        frequency: int | None = None,
        regenerate: bool = False,
    ) -> dict[str, Any]:
        topic = topic.strip()
        if not topic:
            raise ValidationAppError("Topic is required")

        topic_key = normalize_topic_key(topic)
        analysis_context = ""
        document_ids: list[str] = []
        analysis_doc: dict[str, Any] | None = None

        if analysis_id:
            analysis_doc = await self.analysis_repo.get_by_id_and_user(analysis_id, user_id)
            if not analysis_doc:
                raise NotFoundError("Analysis not found")
            analysis_context = self._build_analysis_context(analysis_doc)
            subject = subject or analysis_doc.get("subject")
            document_ids = [str(d) for d in analysis_doc.get("document_ids", [])]

        if not regenerate:
            cached = await self.generated_notes_repo.find_cached(
                user_id, topic_key, analysis_id=analysis_id
            )
            if cached and cached.get("notes"):
                cached_version = (cached.get("ai_metadata") or {}).get("prompt_version")
                if cached_version == PROMPT_VERSION:
                    logger.info("Returning cached notes for topic=%s", topic)
                    return map_generated_note(cached, cached=True)

        existing = await self.generated_notes_repo.find_cached(
            user_id, topic_key, analysis_id=analysis_id
        )
        preserve_saved = bool(existing and existing.get("is_saved"))

        rag_context, rag_sources = await self.rag_retriever.retrieve_for_topic(
            user_id,
            topic,
            subject=subject,
            analysis_document_ids=document_ids or None,
        )

        pipeline_context = ""
        exam_priority = ""
        if analysis_doc:
            pipeline_context = self.notes_pipeline.build_notes_context(
                topic, analysis_doc, frequency=frequency
            )
            if not frequency:
                for row in analysis_doc.get("topic_frequency_table") or []:
                    if str(row.get("topic", "")).lower() == topic.lower():
                        frequency = int(row.get("frequency", 0))
                        break
            exam_priority = self.notes_pipeline.topic_frequency_label(frequency)

        logger.info(
            "Generating notes topic=%s user=%s rag_chunks=%d regenerate=%s",
            topic,
            user_id,
            len(rag_sources),
            regenerate,
        )

        result, metadata = await self.ai_service.generate_topic_notes(
            topic,
            rag_context=rag_context,
            analysis_context=analysis_context,
            subject=subject,
            rag_sources=rag_sources,
            pipeline_context=pipeline_context,
            exam_priority=exam_priority,
        )

        notes_text = (result.get("notes") or result.get("content") or "").strip()
        if not notes_text:
            logger.error("Empty notes returned for topic=%s metadata=%s", topic, metadata)
            raise ValidationAppError(
                "AI returned empty notes. Check API key configuration and try Regenerate."
            )

        upsert_payload: dict[str, Any] = {
                "user_id": self.generated_notes_repo.to_object_id(user_id),
                "topic": topic,
                "topic_key": topic_key,
                "notes": notes_text,
                "summary": result.get("summary"),
                "subject": subject,
                "unit": unit,
                "frequency": frequency,
                "analysis_id": (
                    self.generated_notes_repo.to_object_id(analysis_id)
                    if analysis_id
                    else None
                ),
                "is_saved": preserve_saved,
                "ai_metadata": metadata,
                "rag_sources": rag_sources[:10],
                "generated_at": datetime.now(UTC),
            }
        if result.get("structured"):
            upsert_payload["structured_notes"] = result["structured"]

        note_doc = await self.generated_notes_repo.upsert(
            user_id,
            topic_key,
            upsert_payload,
            analysis_id=analysis_id,
        )

        logger.info("Saved generated notes id=%s topic=%s", note_doc.get("_id"), topic)
        return map_generated_note(note_doc, cached=False)

    async def get_topic_cache_status(
        self,
        user_id: str,
        topic: str,
        *,
        analysis_id: str | None = None,
    ) -> dict[str, Any]:
        topic_key = normalize_topic_key(topic)
        cached = await self.generated_notes_repo.find_cached(
            user_id, topic_key, analysis_id=analysis_id
        )
        return {
            "topic": topic,
            "has_notes": bool(cached and cached.get("notes")),
            "note_id": str(cached["_id"]) if cached else None,
        }

    async def list_generated_notes(
        self,
        user_id: str,
        *,
        page: int = 1,
        limit: int = 20,
        analysis_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = (page - 1) * limit
        notes = await self.generated_notes_repo.list_by_user(
            user_id, skip=skip, limit=limit, analysis_id=analysis_id
        )
        total = await self.generated_notes_repo.count(
            {
                "user_id": self.generated_notes_repo.to_object_id(user_id),
                **(
                    {"analysis_id": self.generated_notes_repo.to_object_id(analysis_id)}
                    if analysis_id
                    else {}
                ),
            }
        )
        return [map_generated_note(n, cached=True) for n in notes], total

    async def get_generated_note(self, note_id: str, user_id: str) -> dict[str, Any]:
        note = await self.generated_notes_repo.get_by_id_and_user(note_id, user_id)
        if not note:
            raise NotFoundError("Generated note not found")
        return map_generated_note(note, cached=True)

    async def save_generated_note(self, note_id: str, user_id: str, is_saved: bool) -> dict[str, Any]:
        note = await self.generated_notes_repo.set_saved(note_id, user_id, is_saved)
        if not note:
            raise NotFoundError("Generated note not found")
        return map_generated_note(note, cached=True)

    async def export_generated_note_pdf(self, note_id: str, user_id: str) -> tuple[bytes, str]:
        note = await self.generated_notes_repo.get_by_id_and_user(note_id, user_id)
        if not note:
            raise NotFoundError("Generated note not found")

        pdf_bytes = generate_note_pdf_bytes(
            note.get("topic", "Study Notes"),
            note.get("notes", ""),
            subject=note.get("subject"),
            topics=[note.get("topic", "")],
        )
        safe_name = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_"
            for c in note.get("topic", "notes")
        ).strip().replace(" ", "_")[:80] or "notes"
        return pdf_bytes, f"{safe_name}.pdf"

    async def list_cached_topics_for_analysis(
        self, user_id: str, analysis_id: str
    ) -> list[str]:
        return await self.generated_notes_repo.list_topic_keys_for_analysis(
            user_id, analysis_id
        )

    async def generate_notes(
        self,
        user_id: str,
        *,
        analysis_id: str | None,
        topics: list[str],
        title: str | None,
        subject: str | None,
        topic: str | None = None,
        unit: str | None = None,
        frequency: int | None = None,
        regenerate: bool = False,
    ) -> dict[str, Any]:
        if topic:
            return await self.generate_topic_note(
                user_id,
                topic,
                analysis_id=analysis_id,
                subject=subject,
                unit=unit,
                frequency=frequency,
                regenerate=regenerate,
            )

        context = ""
        source_id = None
        source_type = NoteSourceType.TOPICS

        if analysis_id:
            analysis = await self.analysis_repo.get_by_id_and_user(analysis_id, user_id)
            if not analysis:
                raise NotFoundError("Analysis not found")
            context = self._build_analysis_context(analysis)
            topics = _topics_from_analysis(analysis, topics)
            source_id = analysis_id
            source_type = NoteSourceType.ANALYSIS
            subject = subject or analysis.get("subject")

        if not topics:
            raise ValidationAppError("At least one topic is required")

        result, metadata = await self.ai_service.generate_notes(topics, context, subject)
        now = datetime.now(UTC)

        note = await self.notes_repo.create(
            {
                "user_id": self.notes_repo.to_object_id(user_id),
                "title": title or result.get("title", "Generated Notes"),
                "type": NoteType.GENERATED,
                "source_type": source_type,
                "source_id": self.notes_repo.to_object_id(source_id) if source_id else None,
                "content": result.get("content", ""),
                "summary": result.get("summary"),
                "topics": result.get("topics", topics),
                "is_favorite": False,
                "ai_metadata": metadata,
                "created_at": now,
                "updated_at": now,
            }
        )

        await self.stats_repo.increment_field(user_id, "notes_count")
        await self.stats_repo.add_activity(
            user_id,
            {
                "type": "note_generated",
                "ref_id": str(note["_id"]),
                "title": note["title"],
                "timestamp": now,
            },
        )
        return map_document_response(note)

    async def simplify_notes(
        self,
        user_id: str,
        *,
        document_id: str | None,
        text: str | None,
        title: str | None,
    ) -> dict[str, Any]:
        content = text or ""
        source_id = None

        if document_id:
            document = await self.document_repo.get_by_id_and_user(document_id, user_id)
            if not document:
                raise NotFoundError("Document not found")
            content = document.get("extracted_text") or ""
            title = title or document.get("title")
            source_id = document_id

        if not content.strip():
            raise ValidationAppError("No content provided for simplification")

        result, metadata = await self.ai_service.simplify_notes(title or "Notes", content)
        now = datetime.now(UTC)

        note = await self.notes_repo.create(
            {
                "user_id": self.notes_repo.to_object_id(user_id),
                "title": title or result.get("title", "Simplified Notes"),
                "type": NoteType.SIMPLIFIED,
                "source_type": NoteSourceType.DOCUMENT if source_id else NoteSourceType.TOPICS,
                "source_id": self.notes_repo.to_object_id(source_id) if source_id else None,
                "content": result.get("content", ""),
                "summary": result.get("summary"),
                "topics": result.get("topics", []),
                "is_favorite": False,
                "ai_metadata": metadata,
                "created_at": now,
                "updated_at": now,
            }
        )

        await self.stats_repo.increment_field(user_id, "notes_count")
        return map_document_response(note)

    async def list_notes(
        self,
        user_id: str,
        *,
        page: int,
        limit: int,
        note_type: str | None = None,
        is_favorite: bool | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = (page - 1) * limit
        notes = await self.notes_repo.list_by_user(
            user_id,
            skip=skip,
            limit=limit,
            note_type=note_type,
            is_favorite=is_favorite,
        )
        total = await self.notes_repo.count_by_user(user_id)
        return [map_document_response(note) for note in notes], total

    async def get_note(self, note_id: str, user_id: str) -> dict[str, Any]:
        note = await self.notes_repo.get_by_id_and_user(note_id, user_id)
        if not note:
            raise NotFoundError("Note not found")
        return map_document_response(note)

    async def export_note_pdf(self, note_id: str, user_id: str) -> tuple[bytes, str]:
        note = await self.notes_repo.get_by_id_and_user(note_id, user_id)
        if not note:
            raise NotFoundError("Note not found")

        pdf_bytes = generate_note_pdf_bytes(
            note.get("title", "Study Notes"),
            note.get("content", ""),
            topics=note.get("topics") or [],
        )
        safe_name = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_" for c in note.get("title", "notes")
        ).strip().replace(" ", "_")[:80] or "notes"
        return pdf_bytes, f"{safe_name}.pdf"

    async def update_note(self, note_id: str, user_id: str, update_data: dict[str, Any]) -> dict[str, Any]:
        filtered = {k: v for k, v in update_data.items() if v is not None}
        note = await self.notes_repo.update(note_id, user_id, filtered)
        if not note:
            raise NotFoundError("Note not found")
        return map_document_response(note)

    async def delete_note(self, note_id: str, user_id: str) -> None:
        deleted = await self.notes_repo.delete(note_id, user_id)
        if not deleted:
            raise NotFoundError("Note not found")
        await self.stats_repo.increment_field(user_id, "notes_count", -1)

    async def clear_notes(self, user_id: str) -> int:
        """Delete all of a user's notes — both batch notes and per-topic AI notes."""
        batch_deleted = await self.notes_repo.delete_all_by_user(user_id)
        topic_deleted = await self.generated_notes_repo.delete_all_by_user(user_id)
        if batch_deleted:
            await self.stats_repo.increment_field(user_id, "notes_count", -batch_deleted)
        return batch_deleted + topic_deleted
