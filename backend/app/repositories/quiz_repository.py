from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.base_repository import BaseRepository


class QuizRepository(BaseRepository):
    collection_name = "quizzes"

    async def create(self, quiz_data: dict[str, Any]) -> dict[str, Any]:
        result = await self.collection.insert_one(quiz_data)
        quiz_data["_id"] = result.inserted_id
        return quiz_data

    async def get_by_id_and_user(self, quiz_id: str, user_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one(
            {"_id": self.to_object_id(quiz_id), "user_id": self.to_object_id(user_id)}
        )

    async def list_by_user(
        self,
        user_id: str,
        *,
        skip: int = 0,
        limit: int = 20,
        subject: str | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"user_id": self.to_object_id(user_id)}
        if subject:
            query["subject"] = subject
        return await self.find_many(query, skip=skip, limit=limit, sort=[("created_at", -1)])

    async def delete(self, quiz_id: str, user_id: str) -> bool:
        result = await self.collection.delete_one(
            {"_id": self.to_object_id(quiz_id), "user_id": self.to_object_id(user_id)}
        )
        return result.deleted_count > 0

    async def delete_all_by_user(self, user_id: str) -> int:
        result = await self.collection.delete_many({"user_id": self.to_object_id(user_id)})
        return result.deleted_count


class QuizAttemptRepository(BaseRepository):
    collection_name = "quiz_attempts"

    async def create(self, attempt_data: dict[str, Any]) -> dict[str, Any]:
        result = await self.collection.insert_one(attempt_data)
        attempt_data["_id"] = result.inserted_id
        return attempt_data

    async def get_by_id_and_user(self, attempt_id: str, user_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one(
            {"_id": self.to_object_id(attempt_id), "user_id": self.to_object_id(user_id)}
        )

    async def list_by_quiz(self, quiz_id: str, user_id: str) -> list[dict[str, Any]]:
        return await self.find_many(
            {"quiz_id": self.to_object_id(quiz_id), "user_id": self.to_object_id(user_id)},
            sort=[("completed_at", -1)],
        )

    async def list_by_user(
        self,
        user_id: str,
        *,
        skip: int = 0,
        limit: int = 20,
        subject: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"user_id": self.to_object_id(user_id)}
        if subject:
            query["subject"] = subject
        if search:
            query["quiz_title"] = {"$regex": search, "$options": "i"}
        return await self.find_many(query, skip=skip, limit=limit, sort=[("completed_at", -1)])

    async def count_by_user(self, user_id: str, *, subject: str | None = None) -> int:
        query: dict[str, Any] = {"user_id": self.to_object_id(user_id)}
        if subject:
            query["subject"] = subject
        return await self.count(query)

    async def delete(self, attempt_id: str, user_id: str) -> bool:
        result = await self.collection.delete_one(
            {"_id": self.to_object_id(attempt_id), "user_id": self.to_object_id(user_id)}
        )
        return result.deleted_count > 0

    async def delete_by_quiz(self, quiz_id: str, user_id: str) -> int:
        result = await self.collection.delete_many(
            {"quiz_id": self.to_object_id(quiz_id), "user_id": self.to_object_id(user_id)}
        )
        return result.deleted_count

    async def avg_score_by_user(self, user_id: str) -> float:
        pipeline = [
            {"$match": {"user_id": self.to_object_id(user_id)}},
            {"$group": {"_id": None, "avg_score": {"$avg": "$score"}}},
        ]
        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)
        if not results:
            return 0.0
        return round(results[0].get("avg_score", 0.0), 2)

    async def score_stats(self, user_id: str, *, subject: str | None = None) -> dict[str, Any]:
        match: dict[str, Any] = {"user_id": self.to_object_id(user_id)}
        if subject:
            match["subject"] = subject
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": None,
                    "avg_score": {"$avg": "$score"},
                    "max_score": {"$max": "$score"},
                    "min_score": {"$min": "$score"},
                    "total_questions": {"$sum": "$total_count"},
                    "count": {"$sum": 1},
                }
            },
        ]
        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)
        if not results:
            return {
                "avg_score": 0.0,
                "max_score": 0.0,
                "min_score": 0.0,
                "total_questions": 0,
                "count": 0,
            }
        row = results[0]
        return {
            "avg_score": round(row.get("avg_score", 0.0) or 0.0, 2),
            "max_score": round(row.get("max_score", 0.0) or 0.0, 2),
            "min_score": round(row.get("min_score", 0.0) or 0.0, 2),
            "total_questions": int(row.get("total_questions", 0) or 0),
            "count": int(row.get("count", 0) or 0),
        }

    async def subject_performance(self, user_id: str) -> list[dict[str, Any]]:
        pipeline = [
            {"$match": {"user_id": self.to_object_id(user_id), "subject": {"$ne": None}}},
            {
                "$group": {
                    "_id": "$subject",
                    "accuracy_percentage": {"$avg": "$score"},
                    "attempts": {"$sum": 1},
                    "quizzes": {"$addToSet": "$quiz_id"},
                }
            },
            {
                "$project": {
                    "subject": "$_id",
                    "accuracy_percentage": {"$round": ["$accuracy_percentage", 2]},
                    "attempts": 1,
                    "quizzes": {"$size": "$quizzes"},
                }
            },
            {"$sort": {"accuracy_percentage": -1}},
        ]
        cursor = self.collection.aggregate(pipeline)
        return await cursor.to_list(length=50)

    async def weekly_progress(self, user_id: str, *, subject: str | None = None) -> list[dict[str, Any]]:
        match: dict[str, Any] = {"user_id": self.to_object_id(user_id)}
        if subject:
            match["subject"] = subject
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-W%V", "date": "$completed_at"}
                    },
                    "average_score": {"$avg": "$score"},
                    "quizzes": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
            {"$limit": 12},
        ]
        cursor = self.collection.aggregate(pipeline)
        rows = await cursor.to_list(length=12)
        return [
            {
                "week": row["_id"],
                "average_score": round(row.get("average_score", 0.0) or 0.0, 2),
                "quizzes": row.get("quizzes", 0),
            }
            for row in rows
        ]

    async def score_trend(
        self, user_id: str, *, subject: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"user_id": self.to_object_id(user_id)}
        if subject:
            query["subject"] = subject
        cursor = self.collection.find(
            query,
            {"score": 1, "subject": 1, "completed_at": 1},
        ).sort("completed_at", 1).limit(limit)
        rows = await cursor.to_list(length=limit)
        return [
            {
                "date": row["completed_at"].strftime("%d %b %Y") if row.get("completed_at") else "",
                "score": row.get("score", 0.0),
                "subject": row.get("subject"),
            }
            for row in rows
        ]


class QuizAnalysisRepository(BaseRepository):
    """Per-user topic accuracy aggregates (updated after each quiz submit)."""

    collection_name = "quiz_analysis"

    async def upsert_topic_stats(
        self,
        user_id: str,
        subject: str | None,
        topic: str,
        *,
        correct: int,
        total: int,
    ) -> None:
        if not topic:
            return
        query = {
            "user_id": self.to_object_id(user_id),
            "topic": topic,
            "subject": subject,
        }
        existing = await self.collection.find_one(query)
        if existing:
            new_correct = existing.get("correct", 0) + correct
            new_total = existing.get("total", 0) + total
            new_attempts = existing.get("attempts", 0) + 1
        else:
            new_correct = correct
            new_total = total
            new_attempts = 1

        accuracy = round((new_correct / new_total) * 100, 2) if new_total else 0.0
        await self.collection.update_one(
            query,
            {
                "$set": {
                    "accuracy_percentage": accuracy,
                    "correct": new_correct,
                    "total": new_total,
                    "attempts": new_attempts,
                    "updated_at": datetime.now(UTC),
                },
                "$setOnInsert": {
                    "user_id": self.to_object_id(user_id),
                    "topic": topic,
                    "subject": subject,
                    "created_at": datetime.now(UTC),
                },
            },
            upsert=True,
        )

    async def list_by_user(
        self,
        user_id: str,
        *,
        subject: str | None = None,
        sort_asc: bool = False,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"user_id": self.to_object_id(user_id)}
        if subject:
            query["subject"] = subject
        direction = 1 if sort_asc else -1
        return await self.find_many(
            query,
            limit=limit,
            sort=[("accuracy_percentage", direction)],
        )
