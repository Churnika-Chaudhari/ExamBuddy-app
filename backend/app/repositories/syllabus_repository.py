"""Persistent per-user syllabus storage (one document per user + subject)."""

from datetime import UTC, datetime
from typing import Any

from app.repositories.base_repository import BaseRepository
from app.utils.subject_matcher import subject_key


class SyllabusRepository(BaseRepository):
    collection_name = "syllabi"

    async def upsert(
        self,
        user_id: str,
        subject: str,
        *,
        modules: list[dict[str, Any]] | None = None,
        module_count: int | None = None,
        topic_count: int | None = None,
        file_reference: dict[str, Any] | None = None,
        source_document_id: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Create or update the user's syllabus for one subject.

        Keyed on (user_id, subject_key) so re-uploading a DBMS syllabus
        replaces the stored modules instead of creating a second row.
        """
        now = datetime.now(UTC)
        normalized = " ".join((subject or "").strip().split())
        key = subject_key(normalized)
        if not key:
            return {}

        query = {"user_id": self.to_object_id(user_id), "subject_key": key}
        set_fields: dict[str, Any] = {
            "subject": normalized,
            "updated_at": now,
        }
        if modules is not None:
            set_fields["modules"] = modules
            set_fields["module_count"] = (
                module_count if module_count is not None else len(modules)
            )
            set_fields["topic_count"] = (
                topic_count
                if topic_count is not None
                else sum(len(m.get("topics") or []) for m in modules)
            )
        elif module_count is not None:
            set_fields["module_count"] = module_count
        if file_reference is not None:
            set_fields["file_reference"] = file_reference
        if source_document_id:
            set_fields["source_document_id"] = source_document_id
        if status:
            set_fields["status"] = status

        result = await self.collection.find_one_and_update(
            query,
            {
                "$set": set_fields,
                "$setOnInsert": {
                    "user_id": self.to_object_id(user_id),
                    "subject_key": key,
                    "created_at": now,
                },
            },
            upsert=True,
            return_document=True,
        )
        return result or {}

    async def list_by_user(self, user_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        return await self.find_many(
            {"user_id": self.to_object_id(user_id)},
            limit=limit,
            sort=[("updated_at", -1)],
        )

    async def get_by_subject(self, user_id: str, subject: str) -> dict[str, Any] | None:
        key = subject_key(subject)
        if not key:
            return None
        return await self.collection.find_one(
            {"user_id": self.to_object_id(user_id), "subject_key": key}
        )

    async def get_by_id_and_user(self, syllabus_id: str, user_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one(
            {"_id": self.to_object_id(syllabus_id), "user_id": self.to_object_id(user_id)}
        )

    async def delete_for_user(self, syllabus_id: str, user_id: str) -> bool:
        result = await self.collection.delete_one(
            {"_id": self.to_object_id(syllabus_id), "user_id": self.to_object_id(user_id)}
        )
        return result.deleted_count > 0
