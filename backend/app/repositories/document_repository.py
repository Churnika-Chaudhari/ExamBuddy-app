from datetime import datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import BaseRepository


class DocumentRepository(BaseRepository):
    collection_name = "documents"

    async def create(self, document_data: dict[str, Any]) -> dict[str, Any]:
        result = await self.collection.insert_one(document_data)
        document_data["_id"] = result.inserted_id
        return document_data

    async def get_by_id_and_user(self, document_id: str, user_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one(
            {"_id": self.to_object_id(document_id), "user_id": self.to_object_id(user_id)}
        )

    async def list_by_user(
        self,
        user_id: str,
        *,
        skip: int = 0,
        limit: int = 20,
        category: str | None = None,
        subject: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"user_id": self.to_object_id(user_id)}
        if category:
            query["category"] = category
        if subject:
            query["subject"] = subject
        if status:
            query["status"] = status
        if search:
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"extracted_text": {"$regex": search, "$options": "i"}},
            ]
        return await self.find_many(query, skip=skip, limit=limit, sort=[("created_at", -1)])

    async def count_by_user(self, user_id: str, filter_query: dict[str, Any] | None = None) -> int:
        query: dict[str, Any] = {"user_id": self.to_object_id(user_id)}
        if filter_query:
            query.update(filter_query)
        return await self.count(query)

    async def update(self, document_id: str, user_id: str, update_data: dict[str, Any]) -> dict[str, Any] | None:
        update_data["updated_at"] = datetime.utcnow()
        await self.collection.update_one(
            {"_id": self.to_object_id(document_id), "user_id": self.to_object_id(user_id)},
            {"$set": update_data},
        )
        return await self.get_by_id_and_user(document_id, user_id)

    async def delete(self, document_id: str, user_id: str) -> bool:
        result = await self.collection.delete_one(
            {"_id": self.to_object_id(document_id), "user_id": self.to_object_id(user_id)}
        )
        return result.deleted_count > 0

    def _user_query(self, user_id: str, category: str | None) -> dict[str, Any]:
        query: dict[str, Any] = {"user_id": self.to_object_id(user_id)}
        if category:
            query["category"] = category
        return query

    async def list_all_by_user(
        self, user_id: str, *, category: str | None = None
    ) -> list[dict[str, Any]]:
        cursor = self.collection.find(self._user_query(user_id, category), {"file_public_id": 1})
        return await cursor.to_list(length=None)

    async def delete_all_by_user(self, user_id: str, *, category: str | None = None) -> int:
        result = await self.collection.delete_many(self._user_query(user_id, category))
        return result.deleted_count

    async def get_many_by_ids(self, document_ids: list[str], user_id: str) -> list[dict[str, Any]]:
        object_ids = [self.to_object_id(doc_id) for doc_id in document_ids]
        cursor = self.collection.find(
            {"_id": {"$in": object_ids}, "user_id": self.to_object_id(user_id)}
        )
        return await cursor.to_list(length=len(object_ids))
