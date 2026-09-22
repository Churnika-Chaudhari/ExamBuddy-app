"""Persist and read back the syllabus a user uploaded for a subject.

The syllabus is the durable structure PYQ analysis is mapped onto, so it lives
in its own collection (`syllabi`) rather than only inside the uploaded
document: documents can be cleared, and a user may re-upload the same subject.
Module extraction itself is NOT reimplemented here — this service stores and
serves what `syllabus_parser` + `syllabus_modules` already produce.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.exceptions import NotFoundError
from app.repositories.syllabus_repository import SyllabusRepository
from app.utils.subject_detector import normalize_subject_name
from app.utils.subject_matcher import canonical_subject_name, subject_key
from app.utils.syllabus_modules import (
    compact_modules_for_storage,
    extract_subject_modules_from_structure,
)

logger = logging.getLogger(__name__)


class SyllabusService:
    def __init__(self, syllabus_repo: SyllabusRepository) -> None:
        self.syllabus_repo = syllabus_repo

    def map_syllabus(self, doc: dict[str, Any]) -> dict[str, Any]:
        modules = doc.get("modules") or []
        return {
            "id": str(doc.get("_id")),
            "subject": doc.get("subject") or "",
            "subject_key": doc.get("subject_key") or "",
            "modules": [
                {
                    "module_id": m.get("module_id"),
                    "module_number": m.get("module_number"),
                    "module_name": m.get("module_name"),
                    "display_name": m.get("display_name"),
                    "topics": m.get("topics") or [],
                    "topic_count": len(m.get("topics") or []),
                }
                for m in modules
            ],
            "module_count": doc.get("module_count") or len(modules),
            "topic_count": doc.get("topic_count")
            or sum(len(m.get("topics") or []) for m in modules),
            "file_reference": doc.get("file_reference"),
            "status": doc.get("status") or "ready",
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
        }

    async def register_pending(
        self,
        user_id: str,
        subject: str | None,
        *,
        file_reference: dict[str, Any] | None = None,
        source_document_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Record the syllabus the moment the file lands.

        Text extraction runs in the background, so the row is created first
        (status `processing`) and filled with modules when parsing finishes.
        Without this, an app restart between upload and extraction would lose
        the fact that a syllabus exists at all.
        """
        name = normalize_subject_name(subject or "")
        if not name:
            return None
        existing = await self.syllabus_repo.get_by_subject(user_id, name)
        saved = await self.syllabus_repo.upsert(
            user_id,
            name,
            file_reference=file_reference,
            source_document_id=source_document_id,
            status="ready" if (existing or {}).get("modules") else "processing",
        )
        return saved or None

    async def save_from_structure(
        self,
        user_id: str,
        structure: dict[str, Any] | None,
        *,
        default_subject: str | None = None,
        file_reference: dict[str, Any] | None = None,
        source_document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Upsert one syllabus row per subject found in a parsed syllabus PDF."""
        if not structure:
            return []

        names: list[str] = []
        for raw in structure.get("subject_names") or []:
            name = normalize_subject_name(str(raw or ""))
            if name:
                names.append(name)
        explicit = normalize_subject_name(default_subject or "")
        if explicit:
            names.insert(0, explicit)

        saved_rows: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        for name in names:
            key = subject_key(name)
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)

            modules = extract_subject_modules_from_structure(
                structure, preferred_subject=name
            )
            compact = compact_modules_for_storage(modules)
            if not compact:
                logger.info(
                    "Syllabus parsed with no modules for subject=%s user=%s", name, user_id
                )
            row = await self.syllabus_repo.upsert(
                user_id,
                name,
                modules=compact,
                file_reference=file_reference,
                source_document_id=source_document_id,
                status="ready" if compact else "no_modules",
            )
            if row:
                saved_rows.append(row)
                logger.info(
                    "Syllabus saved user=%s subject=%s modules=%d",
                    user_id,
                    name,
                    len(compact),
                )
        return saved_rows

    async def list_syllabi(self, user_id: str) -> list[dict[str, Any]]:
        rows = await self.syllabus_repo.list_by_user(user_id)
        return [self.map_syllabus(row) for row in rows if row.get("subject")]

    async def get_for_subject(self, user_id: str, subject: str) -> dict[str, Any]:
        row = await self.syllabus_repo.get_by_subject(user_id, subject)
        if not row:
            raise NotFoundError(f"No saved syllabus for '{subject}'")
        return self.map_syllabus(row)

    async def find_modules_for_subject(
        self, user_id: str, subject: str
    ) -> list[dict[str, Any]]:
        """Stored modules for a subject, alias-matched. Empty when unknown."""
        row = await self.syllabus_repo.get_by_subject(user_id, subject)
        if not row:
            return []
        return list(row.get("modules") or [])

    async def delete_syllabus(self, user_id: str, syllabus_id: str) -> None:
        deleted = await self.syllabus_repo.delete_for_user(syllabus_id, user_id)
        if not deleted:
            raise NotFoundError("Syllabus not found")

    @staticmethod
    def display_subject(subject: str | None) -> str:
        return canonical_subject_name(subject)
