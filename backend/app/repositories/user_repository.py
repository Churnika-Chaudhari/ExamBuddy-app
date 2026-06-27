from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):
    collection_name = "users"

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        return await self.find_by_id(user_id)

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"email": email.lower()})

    async def create(self, user_data: dict[str, Any]) -> dict[str, Any]:
        result = await self.collection.insert_one(user_data)
        user_data["_id"] = result.inserted_id
        return user_data

    async def update(self, user_id: str, update_data: dict[str, Any]) -> dict[str, Any] | None:
        update_data["updated_at"] = datetime.utcnow()
        await self.collection.update_one(
            {"_id": self.to_object_id(user_id)},
            {"$set": update_data},
        )
        return await self.get_by_id(user_id)

    async def set_reset_token(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        await self.collection.update_one(
            {"_id": self.to_object_id(user_id)},
            {
                "$set": {
                    "reset_token_hash": token_hash,
                    "reset_token_expires": expires_at,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

    async def get_by_reset_token_hash(self, token_hash: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"reset_token_hash": token_hash})

    async def clear_reset_token(self, user_id: str) -> None:
        await self.collection.update_one(
            {"_id": self.to_object_id(user_id)},
            {
                "$set": {"updated_at": datetime.utcnow()},
                "$unset": {"reset_token_hash": "", "reset_token_expires": ""},
            },
        )

    async def delete(self, user_id: str) -> bool:
        return await self.delete_by_id(user_id)
