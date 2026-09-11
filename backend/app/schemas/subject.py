from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseSchema


class SubjectResponse(BaseSchema):
    id: str
    name: str
    pyq_count: int = 0
    topic_count: int = 0
    syllabus_count: int = 0
    analyzed_paper_count: int = 0
    last_updated: datetime | None = None
    created_at: datetime | None = None


class SubjectTopicItem(BaseSchema):
    topic: str
    topic_id: str | None = None
    topic_name: str | None = None
    unit: str | None = None
    module_id: str | None = None
    module_number: int | None = None
    module_name: str | None = None
    from_syllabus: bool | None = None
    asked: bool | None = None
    needs_review: bool | None = None
    frequency: int = 1
    occurrence_count: int | None = None
    paper_count: int | None = None
    total_marks: float | None = None
    importance: str | None = None
    priority: str | None = None
    priority_score: float | None = None
    last_occurrence: datetime | None = None
    analysis_ids: list[str] = Field(default_factory=list)


class SubjectModuleItem(BaseSchema):
    module_id: str
    module_number: int | None = None
    module_name: str
    display_name: str | None = None
    is_unmapped: bool = False
    is_fallback: bool = False
    topic_count: int = 0
    asked_topic_count: int = 0
    high_priority_count: int = 0
    question_occurrence: int = 0
    topics: list[SubjectTopicItem] = Field(default_factory=list)
    pyq_topics: list[SubjectTopicItem] = Field(default_factory=list)


class SubjectTopicsResponse(BaseSchema):
    subject_id: str
    subject: str
    topics: list[SubjectTopicItem] = Field(default_factory=list)
    modules: list[SubjectModuleItem] = Field(default_factory=list)
    module_count: int = 0
    has_syllabus_modules: bool = False
    analysis_ids: list[str] = Field(default_factory=list)
    analyzed_paper_count: int = 0
    priority_summary: dict[str, int] = Field(default_factory=dict)


class SubjectPyqFilterRequest(BaseSchema):
    module_ids: list[str] = Field(default_factory=list)
    include_unmapped: bool | None = None


class SubjectPyqFilterResponse(BaseSchema):
    subject_id: str
    subject: str
    modules: list[SubjectModuleItem] = Field(default_factory=list)
    topics: list[SubjectTopicItem] = Field(default_factory=list)
    selected_module_ids: list[str] = Field(default_factory=list)
    empty_modules: list[str] = Field(default_factory=list)
    all_modules: bool = False
    analysis_ids: list[str] = Field(default_factory=list)
    analyzed_paper_count: int = 0
