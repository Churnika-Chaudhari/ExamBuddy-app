from datetime import UTC, datetime
from typing import Any

from app.repositories.base_repository import BaseRepository


class SubjectRepository(BaseRepository):
    collection_name = "subjects"

    async def upsert(
        self,
        user_id: str,
        name: str,
        *,
        pyq_count: int | None = None,
        topic_count: int | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        normalized = " ".join(name.strip().split())
        query = {
            "user_id": self.to_object_id(user_id),
            "name": normalized,
        }
        set_fields: dict[str, Any] = {"updated_at": now, "last_updated": now}
        if pyq_count is not None:
            set_fields["pyq_count"] = pyq_count
        if topic_count is not None:
            set_fields["topic_count"] = topic_count
        set_fields.setdefault("pyq_count", 0)
        set_fields.setdefault("topic_count", 0)

        result = await self.collection.find_one_and_update(
            query,
            {
                "$set": set_fields,
                "$setOnInsert": {
                    "user_id": self.to_object_id(user_id),
                    "name": normalized,
                    "created_at": now,
                },
            },
            upsert=True,
            return_document=True,
        )
        return result or {}

    async def increment_pyq(self, user_id: str, name: str, delta: int = 1) -> None:
        now = datetime.now(UTC)
        normalized = " ".join(name.strip().split())
        await self.collection.update_one(
            {"user_id": self.to_object_id(user_id), "name": normalized},
            {
                "$inc": {"pyq_count": delta},
                "$set": {"updated_at": now, "last_updated": now},
                "$setOnInsert": {
                    "user_id": self.to_object_id(user_id),
                    "name": normalized,
                    "topic_count": 0,
                    "created_at": now,
                },
            },
            upsert=True,
        )

    async def set_topic_count(self, user_id: str, name: str, topic_count: int) -> None:
        now = datetime.now(UTC)
        normalized = " ".join(name.strip().split())
        await self.collection.update_one(
            {"user_id": self.to_object_id(user_id), "name": normalized},
            {
                "$set": {
                    "topic_count": topic_count,
                    "updated_at": now,
                    "last_updated": now,
                },
                "$setOnInsert": {
                    "user_id": self.to_object_id(user_id),
                    "name": normalized,
                    "pyq_count": 0,
                    "created_at": now,
                },
            },
            upsert=True,
        )

    async def list_by_user(self, user_id: str) -> list[dict[str, Any]]:
        return await self.find_many(
            {"user_id": self.to_object_id(user_id), "hidden": {"$ne": True}},
            limit=100,
            sort=[("name", 1)],
        )

    async def set_hidden(self, subject_id: str, user_id: str, hidden: bool = True) -> bool:
        result = await self.collection.update_one(
            {"_id": self.to_object_id(subject_id), "user_id": self.to_object_id(user_id)},
            {"$set": {"hidden": hidden, "updated_at": datetime.now(UTC)}},
        )
        return result.matched_count > 0

    async def get_by_id_and_user(self, subject_id: str, user_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one(
            {"_id": self.to_object_id(subject_id), "user_id": self.to_object_id(user_id)}
        )

    async def get_by_name(self, user_id: str, name: str) -> dict[str, Any] | None:
        normalized = " ".join(name.strip().split())
        return await self.collection.find_one(
            {"user_id": self.to_object_id(user_id), "name": normalized}
        )
