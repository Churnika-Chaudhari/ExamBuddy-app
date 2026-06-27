from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class BaseRepository:
    collection_name: str = ""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.collection = db[self.collection_name]

    @staticmethod
    def to_object_id(value: str) -> ObjectId:
        if not ObjectId.is_valid(value):
            raise ValueError(f"Invalid ObjectId: {value}")
        return ObjectId(value)

    async def find_by_id(self, doc_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"_id": self.to_object_id(doc_id)})

    async def delete_by_id(self, doc_id: str) -> bool:
        result = await self.collection.delete_one({"_id": self.to_object_id(doc_id)})
        return result.deleted_count > 0

    async def count(self, filter_query: dict[str, Any] | None = None) -> int:
        return await self.collection.count_documents(filter_query or {})

    async def find_many(
        self,
        filter_query: dict[str, Any],
        *,
        skip: int = 0,
        limit: int = 20,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[dict[str, Any]]:
        cursor = self.collection.find(filter_query)
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
