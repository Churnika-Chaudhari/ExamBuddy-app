import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.users.create_index("email", unique=True)
    await db.users.create_index("reset_token_hash", sparse=True)

    await db.documents.create_index([("user_id", 1), ("created_at", -1)])
    await db.documents.create_index([("user_id", 1), ("category", 1)])
    await db.documents.create_index([("user_id", 1), ("subject", 1)])
    await db.documents.create_index([("user_id", 1), ("status", 1)])

    await db.pyq_analyses.create_index([("user_id", 1), ("created_at", -1)])
    await db.pyq_analyses.create_index("status")

    await db.notes.create_index([("user_id", 1), ("created_at", -1)])
    await db.notes.create_index([("user_id", 1), ("is_favorite", 1)])

    await db.generated_notes.create_index(
        [("user_id", 1), ("topic_key", 1), ("analysis_id", 1)],
        unique=True,
    )
    await db.generated_notes.create_index([("user_id", 1), ("updated_at", -1)])
    await db.generated_notes.create_index([("user_id", 1), ("analysis_id", 1)])

    await db.subjects.create_index([("user_id", 1), ("name", 1)], unique=True)
    await db.subjects.create_index([("user_id", 1), ("last_updated", -1)])

    await db.quizzes.create_index([("user_id", 1), ("created_at", -1)])
    await db.quizzes.create_index([("user_id", 1), ("subject", 1)])
    await db.quiz_attempts.create_index([("user_id", 1), ("completed_at", -1)])
    await db.quiz_attempts.create_index([("user_id", 1), ("subject", 1)])
    await db.quiz_attempts.create_index("quiz_id")
    await db.quiz_analysis.create_index([("user_id", 1), ("subject", 1), ("topic", 1)], unique=True)
    await db.quiz_analysis.create_index([("user_id", 1), ("accuracy_percentage", 1)])

    await db.user_stats.create_index("user_id", unique=True)

    logger.info("MongoDB indexes created successfully")
