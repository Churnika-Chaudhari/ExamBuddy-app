from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import BaseRepository


class AnalysisRepository(BaseRepository):
    collection_name = "pyq_analyses"

    async def create(self, analysis_data: dict[str, Any]) -> dict[str, Any]:
        result = await self.collection.insert_one(analysis_data)
        analysis_data["_id"] = result.inserted_id
        return analysis_data

    async def get_by_id_and_user(self, analysis_id: str, user_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one(
            {"_id": self.to_object_id(analysis_id), "user_id": self.to_object_id(user_id)}
        )

    async def list_by_user(self, user_id: str, *, skip: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        return await self.find_many(
            {"user_id": self.to_object_id(user_id)},
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)],
        )

    async def update(self, analysis_id: str, update_data: dict[str, Any]) -> dict[str, Any] | None:
        await self.collection.update_one(
            {"_id": self.to_object_id(analysis_id)},
            {"$set": update_data},
        )
        return await self.find_by_id(analysis_id)

    async def delete(self, analysis_id: str, user_id: str) -> bool:
        result = await self.collection.delete_one(
            {"_id": self.to_object_id(analysis_id), "user_id": self.to_object_id(user_id)}
        )
        return result.deleted_count > 0

    async def count_by_user(self, user_id: str) -> int:
        return await self.count({"user_id": self.to_object_id(user_id)})
