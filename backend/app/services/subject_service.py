import logging
from typing import Any

from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.generated_notes_repository import GeneratedNotesRepository
from app.repositories.subject_repository import SubjectRepository
from app.services.mappers import map_document_response
from app.services.quiz_service import _topics_from_analysis_doc
from app.utils.subject_detector import normalize_subject_name, resolve_document_subject

logger = logging.getLogger(__name__)


class SubjectService:
    def __init__(
        self,
        subject_repo: SubjectRepository,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        generated_notes_repo: GeneratedNotesRepository | None = None,
    ) -> None:
        self.subject_repo = subject_repo
        self.document_repo = document_repo
        self.analysis_repo = analysis_repo
        self.generated_notes_repo = generated_notes_repo

    def _map_subject(self, doc: dict[str, Any]) -> dict[str, Any]:
        mapped = map_document_response(doc)
        return {
            "id": mapped.get("id"),
            "name": doc.get("name", ""),
            "pyq_count": doc.get("pyq_count", 0),
            "topic_count": doc.get("topic_count", 0),
            "last_updated": mapped.get("last_updated") or mapped.get("updated_at"),
            "created_at": mapped.get("created_at"),
        }

    def _resolve_doc_subject(self, doc: dict[str, Any]) -> str | None:
        return resolve_document_subject(
            explicit_subject=doc.get("subject"),
            filename=doc.get("title"),
            title=doc.get("title"),
            extracted_text=doc.get("extracted_text"),
        )

    async def sync_all_for_user(self, user_id: str) -> None:
        """Rebuild subject counts from PYQs, completed analyses, and generated notes."""
        counts: dict[str, dict[str, int]] = {}

        def _ensure(name: str) -> dict[str, int]:
            key = normalize_subject_name(name)
            if not key:
                return {}
            # Case-insensitive merge so "WebX" and "webx" stay one subject.
            for existing in list(counts):
                if existing.lower() == key.lower():
                    return counts[existing]
            counts[key] = {"pyq_count": 0, "topic_count": 0}
            return counts[key]

        docs = await self.document_repo.list_by_user(
            user_id, skip=0, limit=500, category="pyq"
        )
        for doc in docs:
            subject = self._resolve_doc_subject(doc)
            if not subject:
                continue
            bucket = _ensure(subject)
            if bucket:
                bucket["pyq_count"] += 1

        # Uploaded notes with a subject also surface in the quiz subject list.
        notes_docs = await self.document_repo.list_by_user(
            user_id, skip=0, limit=500, category="notes"
        )
        for doc in notes_docs:
            subject = self._resolve_doc_subject(doc)
            if not subject:
                continue
            _ensure(subject)

        analyses = await self.analysis_repo.list_by_user(user_id, limit=200)
        for analysis in analyses:
            if analysis.get("status") != "completed":
                continue
            subject = normalize_subject_name(analysis.get("subject") or "")
            if not subject:
                doc_ids = [str(d) for d in (analysis.get("document_ids") or [])]
                if doc_ids:
                    linked = await self.document_repo.get_many_by_ids(doc_ids, user_id)
                    for doc in linked:
                        subject = self._resolve_doc_subject(doc) or ""
                        if subject:
                            break
            if not subject:
                continue
            topics = _topics_from_analysis_doc(analysis)
            bucket = _ensure(subject)
            if bucket:
                bucket["topic_count"] = max(bucket["topic_count"], len(topics))
                # Ensure analyzed papers appear even when document.subject was blank.
                if bucket["pyq_count"] == 0:
                    bucket["pyq_count"] = max(1, len(analysis.get("document_ids") or [1]))

        # Generated notes subjects (topic/batch notes) also appear dynamically.
        if self.generated_notes_repo:
            try:
                generated = await self.generated_notes_repo.list_by_user(
                    user_id, skip=0, limit=500
                )
                for note in generated:
                    subject = normalize_subject_name(note.get("subject") or "")
                    if subject:
                        _ensure(subject)
            except Exception as exc:
                logger.warning("Could not sync subjects from generated notes: %s", exc)

        for name, data in counts.items():
            await self.subject_repo.upsert(
                user_id,
                name,
                pyq_count=data["pyq_count"],
                topic_count=data["topic_count"],
                unhide=True,
            )

    async def on_pyq_uploaded(self, user_id: str, subject: str) -> None:
        if not subject:
            return
        await self.subject_repo.increment_pyq(user_id, subject)
        logger.info("Subject updated on PYQ upload: %s", subject)

    async def on_analysis_completed(self, user_id: str, subject: str, topic_count: int) -> None:
        if not subject:
            return
        await self.subject_repo.set_topic_count(user_id, subject, topic_count)
        logger.info("Subject topics updated: %s count=%d", subject, topic_count)

    async def list_subjects(self, user_id: str) -> list[dict[str, Any]]:
        await self.sync_all_for_user(user_id)
        subjects = await self.subject_repo.list_by_user(user_id)
        return [self._map_subject(s) for s in subjects if s.get("name")]

    async def get_subject_topics(self, user_id: str, subject_id: str) -> dict[str, Any]:
        from bson import ObjectId

        from app.core.exceptions import NotFoundError

        if ObjectId.is_valid(subject_id):
            subject_doc = await self.subject_repo.get_by_id_and_user(subject_id, user_id)
        else:
            subject_doc = await self.subject_repo.get_by_name(user_id, subject_id)

        if not subject_doc:
            raise NotFoundError("Subject not found")

        subject_name = subject_doc.get("name", "")
        analyses = await self.analysis_repo.list_by_user(user_id, limit=200)
        topic_map: dict[str, dict[str, Any]] = {}
        analysis_ids: list[str] = []

        for analysis in analyses:
            if analysis.get("status") != "completed":
                continue
            a_subject = normalize_subject_name(analysis.get("subject") or "")
            if a_subject.lower() != subject_name.lower():
                continue
            analysis_ids.append(str(analysis["_id"]))
            for row in _topics_from_analysis_doc(analysis):
                key = row["topic"].lower()
                if key not in topic_map or row["frequency"] > topic_map[key]["frequency"]:
                    topic_map[key] = row

        topics = sorted(topic_map.values(), key=lambda x: x.get("frequency", 0), reverse=True)
        return {
            "subject_id": str(subject_doc["_id"]),
            "subject": subject_name,
            "topics": topics,
            "analysis_ids": analysis_ids,
        }

    async def get_subject_overview(self, user_id: str, subject_id: str) -> dict[str, Any]:
        """
        Consolidated view for the Subject Notes screen: every topic extracted
        across all of the subject's PYQs, plus the source documents the notes
        will be generated from (PYQs, uploaded notes, study materials).
        """
        topics_data = await self.get_subject_topics(user_id, subject_id)
        subject_name = topics_data["subject"]
        target = normalize_subject_name(subject_name).strip().lower()

        docs = await self.document_repo.list_by_user(user_id, skip=0, limit=300)
        source_documents: list[dict[str, Any]] = []
        counts = {"pyq": 0, "notes": 0, "syllabus": 0, "study_material": 0, "other": 0}

        for doc in docs:
            resolved = resolve_document_subject(
                explicit_subject=doc.get("subject"),
                filename=doc.get("title"),
                title=doc.get("title"),
            )
            doc_subject = normalize_subject_name(resolved or "").strip().lower()
            if doc_subject != target:
                continue
            category = doc.get("category") or "other"
            counts[category] = counts.get(category, 0) + 1
            source_documents.append(
                {
                    "id": str(doc["_id"]),
                    "title": doc.get("title") or "Untitled",
                    "category": category,
                    "status": doc.get("status"),
                    "page_count": doc.get("page_count"),
                }
            )

        return {
            "subject_id": topics_data["subject_id"],
            "subject": subject_name,
            "topics": topics_data["topics"],
            "analysis_ids": topics_data["analysis_ids"],
            "source_documents": source_documents,
            "pyq_count": counts.get("pyq", 0),
            "notes_count": counts.get("notes", 0),
            "syllabus_count": counts.get("syllabus", 0),
            "study_material_count": counts.get("study_material", 0),
            "total_sources": len(source_documents),
        }

    async def hide_subject(self, user_id: str, subject_id: str) -> None:
        # Soft-remove: the subject list is rebuilt from PYQs on each fetch, so a
        # hard delete would reappear. Hiding keeps it out of the list for good.
        ok = await self.subject_repo.set_hidden(subject_id, user_id, True)
        if not ok:
            from app.core.exceptions import NotFoundError

            raise NotFoundError("Subject not found")

    async def get_subject_name_by_id(self, user_id: str, subject_id: str) -> str:
        subject_doc = await self.subject_repo.get_by_id_and_user(subject_id, user_id)
        if not subject_doc:
            from app.core.exceptions import NotFoundError

            raise NotFoundError("Subject not found")
        return subject_doc.get("name", "")
