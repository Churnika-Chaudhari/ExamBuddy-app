"""Repository for per-topic cached AI study notes (GeneratedNotes collection)."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


def normalize_topic_key(topic: str) -> str:
    key = topic.strip().lower()
    key = re.sub(r"[^a-z0-9\s\-/+]", "", key)
    return re.sub(r"\s+", " ", key).strip()


class GeneratedNotesRepository(BaseRepository):
    collection_name = "generated_notes"

    async def find_cached(
        self,
        user_id: str,
        topic_key: str,
        *,
        analysis_id: str | None = None,
    ) -> dict[str, Any] | None:
        query: dict[str, Any] = {
            "user_id": self.to_object_id(user_id),
            "topic_key": topic_key,
        }
        if analysis_id:
            query["analysis_id"] = self.to_object_id(analysis_id)
        else:
            query["analysis_id"] = None
        return await self.collection.find_one(query)

    async def upsert(
        self,
        user_id: str,
        topic_key: str,
        data: dict[str, Any],
        *,
        analysis_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Upsert generated note.

        IMPORTANT: MongoDB forbids the same field in $set and $setOnInsert.
        created_at → $setOnInsert only
        generated_at / updated_at → $set only
        """
        query: dict[str, Any] = {
            "user_id": self.to_object_id(user_id),
            "topic_key": topic_key,
        }
        if analysis_id:
            query["analysis_id"] = self.to_object_id(analysis_id)
        else:
            query["analysis_id"] = None

        now = datetime.now(UTC)

        set_data = {
            k: v
            for k, v in data.items()
            if k not in {"created_at", "_id"}
        }
        set_data["updated_at"] = now
        set_data.setdefault("generated_at", now)

        result = await self.collection.find_one_and_update(
            query,
            {
                "$set": set_data,
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
            return_document=True,
        )
        if result is None:
            logger.error("Upsert returned None for topic_key=%s", topic_key)
            raise RuntimeError("Failed to save generated notes to database")
        return result

    async def get_by_id_and_user(self, note_id: str, user_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one(
            {"_id": self.to_object_id(note_id), "user_id": self.to_object_id(user_id)}
        )

    async def list_by_user(
        self,
        user_id: str,
        *,
        skip: int = 0,
        limit: int = 50,
        analysis_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"user_id": self.to_object_id(user_id)}
        if analysis_id:
            query["analysis_id"] = self.to_object_id(analysis_id)
        return await self.find_many(
            query, skip=skip, limit=limit, sort=[("updated_at", -1)]
        )

    async def set_saved(self, note_id: str, user_id: str, is_saved: bool) -> dict[str, Any] | None:
        await self.collection.update_one(
            {"_id": self.to_object_id(note_id), "user_id": self.to_object_id(user_id)},
            {"$set": {"is_saved": is_saved, "updated_at": datetime.now(UTC)}},
        )
        return await self.get_by_id_and_user(note_id, user_id)

    async def delete_by_id(self, note_id: str, user_id: str) -> bool:
        result = await self.collection.delete_one(
            {"_id": self.to_object_id(note_id), "user_id": self.to_object_id(user_id)}
        )
        return result.deleted_count > 0

    async def delete_all_by_user(self, user_id: str) -> int:
        result = await self.collection.delete_many({"user_id": self.to_object_id(user_id)})
        return result.deleted_count

    async def list_topic_keys_for_analysis(
        self, user_id: str, analysis_id: str
    ) -> list[str]:
        cursor = self.collection.find(
            {
                "user_id": self.to_object_id(user_id),
                "analysis_id": self.to_object_id(analysis_id),
            },
            {"topic_key": 1},
        )
        docs = await cursor.to_list(length=200)
        return [d["topic_key"] for d in docs if d.get("topic_key")]
