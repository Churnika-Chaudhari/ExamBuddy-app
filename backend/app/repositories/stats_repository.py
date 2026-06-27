from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import BaseRepository


class StatsRepository(BaseRepository):
    collection_name = "user_stats"

    async def get_by_user(self, user_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"user_id": self.to_object_id(user_id)})

    async def upsert(self, user_id: str, update_data: dict[str, Any]) -> dict[str, Any]:
        update_data["updated_at"] = datetime.now(UTC)
        await self.collection.update_one(
            {"user_id": self.to_object_id(user_id)},
            {"$set": update_data},
            upsert=True,
        )
        return await self.get_by_user(user_id)  # type: ignore[return-value]

    async def increment_field(self, user_id: str, field: str, amount: int = 1) -> None:
        await self.collection.update_one(
            {"user_id": self.to_object_id(user_id)},
            {
                "$inc": {field: amount},
                "$set": {"updated_at": datetime.now(UTC)},
            },
            upsert=True,
        )

    async def add_activity(self, user_id: str, activity: dict[str, Any], max_items: int = 10) -> None:
        await self.collection.update_one(
            {"user_id": self.to_object_id(user_id)},
            {
                "$push": {
                    "recent_activity": {
                        "$each": [activity],
                        "$position": 0,
                        "$slice": max_items,
                    }
                },
                "$set": {"updated_at": datetime.now(UTC)},
            },
            upsert=True,
        )

    async def clear_activities(self, user_id: str) -> None:
        await self.collection.update_one(
            {"user_id": self.to_object_id(user_id)},
            {"$set": {"recent_activity": [], "updated_at": datetime.now(UTC)}},
            upsert=True,
        )

    async def remove_activity(
        self,
        user_id: str,
        *,
        ref_id: str,
        activity_type: str,
    ) -> bool:
        result = await self.collection.update_one(
            {"user_id": self.to_object_id(user_id)},
            {
                "$pull": {
                    "recent_activity": {
                        "ref_id": ref_id,
                        "type": activity_type,
                    }
                },
                "$set": {"updated_at": datetime.now(UTC)},
            },
        )
        return result.modified_count > 0
