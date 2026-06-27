from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import BaseSchema


class SubjectResponse(BaseSchema):
    id: str
    name: str
    pyq_count: int = 0
    topic_count: int = 0
    last_updated: datetime | None = None
    created_at: datetime | None = None


class SubjectTopicItem(BaseSchema):
    topic: str
    unit: str | None = None
    frequency: int = 1
    importance: str | None = None


class SubjectTopicsResponse(BaseSchema):
    subject_id: str
    subject: str
    topics: list[SubjectTopicItem] = Field(default_factory=list)
    analysis_ids: list[str] = Field(default_factory=list)
