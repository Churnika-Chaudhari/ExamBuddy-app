import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from bson import ObjectId

from app.repositories.generated_notes_repository import GeneratedNotesRepository


async def main() -> None:
    coll = MagicMock()
    coll.find_one_and_update = AsyncMock(return_value={"_id": ObjectId(), "notes": "x"})
    repo = GeneratedNotesRepository.__new__(GeneratedNotesRepository)
    repo.collection = coll

    await repo.upsert(
        "674a1f2d3b4c5d6e7f8a9b01",
        "cloud computing",
        {"topic": "Cloud", "notes": "n", "generated_at": datetime.now(UTC)},
        analysis_id="674a1f2d3b4c5d6e7f8a9b02",
    )
    update_doc = coll.find_one_and_update.call_args[0][1]
    assert "generated_at" not in update_doc["$setOnInsert"]
    assert "generated_at" in update_doc["$set"]
    assert not (set(update_doc["$set"]) & set(update_doc["$setOnInsert"]))
    print("OK: no MongoDB operator conflict")


if __name__ == "__main__":
    asyncio.run(main())
