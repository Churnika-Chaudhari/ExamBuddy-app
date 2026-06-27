from datetime import datetime

from pydantic import Field

from app.schemas.auth import UserPreferences
from app.schemas.common import BaseSchema


class ProfileUpdateRequest(BaseSchema):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    institution: str | None = Field(default=None, max_length=200)
    course: str | None = Field(default=None, max_length=200)


class ChangePasswordRequest(BaseSchema):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class PreferencesUpdateRequest(BaseSchema):
    preferences: UserPreferences


class DashboardStats(BaseSchema):
    documents_count: int = 0
    analyses_count: int = 0
    notes_count: int = 0
    quizzes_taken: int = 0
    avg_quiz_score: float = 0.0


class RecentActivity(BaseSchema):
    type: str
    ref_id: str
    title: str
    timestamp: datetime


class DashboardResponse(BaseSchema):
    stats: DashboardStats
    recent_activity: list[RecentActivity] = []
