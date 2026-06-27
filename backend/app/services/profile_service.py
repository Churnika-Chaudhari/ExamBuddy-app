from typing import Any

from app.core.exceptions import NotFoundError, UnauthorizedError, ValidationAppError
from app.core.security import get_password_hash, verify_password
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.notes_repository import NotesRepository
from app.repositories.quiz_repository import QuizAttemptRepository
from app.repositories.stats_repository import StatsRepository
from app.repositories.user_repository import UserRepository
from app.services.file_service import FileService
from app.services.mappers import map_user_response


class ProfileService:
    def __init__(
        self,
        user_repo: UserRepository,
        stats_repo: StatsRepository,
        document_repo: DocumentRepository,
        analysis_repo: AnalysisRepository,
        notes_repo: NotesRepository,
        attempt_repo: QuizAttemptRepository,
        file_service: FileService | None = None,
    ) -> None:
        self.user_repo = user_repo
        self.stats_repo = stats_repo
        self.document_repo = document_repo
        self.analysis_repo = analysis_repo
        self.notes_repo = notes_repo
        self.attempt_repo = attempt_repo
        self.file_service = file_service or FileService()

    async def get_profile(self, user: dict[str, Any]) -> dict[str, Any]:
        return map_user_response(user)

    async def update_profile(self, user_id: str, update_data: dict[str, Any]) -> dict[str, Any]:
        filtered = {k: v for k, v in update_data.items() if v is not None}
        user = await self.user_repo.update(user_id, filtered)
        if not user:
            raise NotFoundError("User not found")
        return map_user_response(user)

    async def update_preferences(self, user_id: str, preferences: dict[str, Any]) -> dict[str, Any]:
        user = await self.user_repo.update(user_id, {"preferences": preferences})
        if not user:
            raise NotFoundError("User not found")
        return map_user_response(user)

    async def change_password(
        self,
        user: dict[str, Any],
        current_password: str,
        new_password: str,
    ) -> dict[str, str]:
        if not verify_password(current_password, user["password_hash"]):
            raise UnauthorizedError("Current password is incorrect")
        await self.user_repo.update(
            str(user["_id"]),
            {"password_hash": get_password_hash(new_password)},
        )
        return {"message": "Password updated successfully"}

    async def get_dashboard(self, user_id: str) -> dict[str, Any]:
        # Always compute counts from the live collections so the dashboard is
        # consistent with the real data. Relying on stored increment/decrement
        # counters lets them drift whenever anything is added, deleted, or
        # cleared — computing on read keeps every screen in sync automatically.
        documents_count = await self.document_repo.count_by_user(user_id)
        analyses_count = await self.analysis_repo.count_by_user(user_id)
        notes_count = await self.notes_repo.count_by_user(user_id)
        quizzes_taken = await self.attempt_repo.count_by_user(user_id)
        avg_quiz_score = await self.attempt_repo.avg_score_by_user(user_id)

        stats_doc = await self.stats_repo.get_by_user(user_id)
        recent_activity = stats_doc.get("recent_activity", []) if stats_doc else []

        # Keep the cached counters aligned with the freshly computed values so
        # any other reader of user_stats sees the same numbers.
        await self.stats_repo.upsert(
            user_id,
            {
                "user_id": self.stats_repo.to_object_id(user_id),
                "documents_count": documents_count,
                "analyses_count": analyses_count,
                "notes_count": notes_count,
                "quizzes_taken": quizzes_taken,
                "avg_quiz_score": avg_quiz_score,
            },
        )

        return {
            "stats": {
                "documents_count": documents_count,
                "analyses_count": analyses_count,
                "notes_count": notes_count,
                "quizzes_taken": quizzes_taken,
                "avg_quiz_score": avg_quiz_score,
            },
            "recent_activity": self._serialize_activities(recent_activity),
        }

    @staticmethod
    def _serialize_activities(activities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = []
        for item in activities:
            ts = item.get("timestamp")
            if hasattr(ts, "isoformat"):
                ts = ts.isoformat()
            serialized.append(
                {
                    "type": item.get("type", ""),
                    "ref_id": str(item.get("ref_id", "")),
                    "title": item.get("title", ""),
                    "timestamp": ts,
                }
            )
        return serialized

    async def clear_recent_activity(self, user_id: str) -> dict[str, Any]:
        await self.stats_repo.clear_activities(user_id)
        return await self.get_dashboard(user_id)

    async def delete_recent_activity(
        self,
        user_id: str,
        *,
        ref_id: str,
        activity_type: str,
    ) -> dict[str, Any]:
        removed = await self.stats_repo.remove_activity(
            user_id,
            ref_id=ref_id,
            activity_type=activity_type,
        )
        if not removed:
            raise NotFoundError("Activity not found")
        return await self.get_dashboard(user_id)

    async def delete_account(self, user_id: str) -> None:
        deleted = await self.user_repo.delete(user_id)
        if not deleted:
            raise NotFoundError("User not found")
