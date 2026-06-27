from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import BaseRepository


class NotesRepository(BaseRepository):
    collection_name = "notes"

    async def create(self, note_data: dict[str, Any]) -> dict[str, Any]:
        result = await self.collection.insert_one(note_data)
        note_data["_id"] = result.inserted_id
        return note_data

    async def get_by_id_and_user(self, note_id: str, user_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one(
            {"_id": self.to_object_id(note_id), "user_id": self.to_object_id(user_id)}
        )

    async def list_by_user(
        self,
        user_id: str,
        *,
        skip: int = 0,
        limit: int = 20,
        note_type: str | None = None,
        is_favorite: bool | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"user_id": self.to_object_id(user_id)}
        if note_type:
            query["type"] = note_type
        if is_favorite is not None:
            query["is_favorite"] = is_favorite
        return await self.find_many(query, skip=skip, limit=limit, sort=[("created_at", -1)])

    async def update(self, note_id: str, user_id: str, update_data: dict[str, Any]) -> dict[str, Any] | None:
        update_data["updated_at"] = datetime.utcnow()
        await self.collection.update_one(
            {"_id": self.to_object_id(note_id), "user_id": self.to_object_id(user_id)},
            {"$set": update_data},
        )
        return await self.get_by_id_and_user(note_id, user_id)

    async def delete(self, note_id: str, user_id: str) -> bool:
        result = await self.collection.delete_one(
            {"_id": self.to_object_id(note_id), "user_id": self.to_object_id(user_id)}
        )
        return result.deleted_count > 0

    async def delete_all_by_user(self, user_id: str) -> int:
        result = await self.collection.delete_many({"user_id": self.to_object_id(user_id)})
        return result.deleted_count

    async def count_by_user(self, user_id: str) -> int:
        return await self.count({"user_id": self.to_object_id(user_id)})
