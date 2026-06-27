from datetime import datetime

from pydantic import Field

from app.models.enums import AnalysisStatus
from app.schemas.common import BaseSchema


class RepeatedQuestion(BaseSchema):
    text: str
    occurrences: list[str] = []
    frequency: int = 1
    similarity_group_id: str | None = None


class ImportantTopic(BaseSchema):
    topic: str
    score: float
    reason: str | None = None


class TopicTableRow(BaseSchema):
    topic: str
    frequency: int
    importance: str


class TopicFrequencyRow(BaseSchema):
    topic: str
    unit: str
    frequency: int


class TopicGroup(BaseSchema):
    group: str
    topics: list[str] = []


class ExamPattern(BaseSchema):
    pattern: str
    description: str
    confidence: float = 0.0


class AIMetadata(BaseSchema):
    provider: str | None = None
    model: str | None = None
    tokens_used: int | None = None
    prompt_version: str | None = None


class PYQAnalysisCreateRequest(BaseSchema):
    document_ids: list[str] = Field(min_length=1, max_length=50)
    subject: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=200)


class PYQAnalysisResponse(BaseSchema):
    id: str
    user_id: str
    document_ids: list[str]
    subject: str | None = None
    title: str
    status: AnalysisStatus
    repeated_questions: list[RepeatedQuestion] = []
    topic_frequency: dict[str, int] = {}
    important_topics: list[ImportantTopic] = []
    topic_table: list[TopicTableRow] = []
    academic_topic_table: list[TopicTableRow] = []
    topic_frequency_table: list[TopicFrequencyRow] = []
    high_priority_topics: list[TopicFrequencyRow] = []
    medium_priority_topics: list[TopicFrequencyRow] = []
    low_priority_topics: list[TopicFrequencyRow] = []
    predicted_important_topics: list[TopicFrequencyRow] = []
    most_important_topics: list[TopicTableRow] = []
    frequently_asked_topics: list[TopicTableRow] = []
    rarely_asked_topics: list[TopicTableRow] = []
    topic_groups: list[TopicGroup] = []
    syllabus_topics: list[str] = []
    exam_patterns: list[ExamPattern] = []
    summary: str | None = None
    ai_metadata: AIMetadata | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


class PYQAnalysisStatusResponse(BaseSchema):
    id: str
    status: AnalysisStatus
    error_message: str | None = None
