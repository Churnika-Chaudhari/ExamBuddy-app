import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    global _client, _database
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    _database = _client[settings.mongodb_db_name]
    await _client.admin.command("ping")
    logger.info("Connected to MongoDB: %s", settings.mongodb_db_name)


async def close_mongo_connection() -> None:
    global _client, _database
    if _client is not None:
        _client.close()
        _client = None
        _database = None
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    if _database is None:
        raise RuntimeError("Database is not initialized. Call connect_to_mongo() first.")
    return _database


def serialize_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is None:
        return None
    result = dict(doc)
    if "_id" in result:
        result["id"] = str(result.pop("_id"))
    if "user_id" in result and result["user_id"] is not None:
        result["user_id"] = str(result["user_id"])
    return result


def serialize_docs(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [serialize_doc(doc) for doc in docs if doc is not None]
