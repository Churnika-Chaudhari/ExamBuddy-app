from datetime import datetime

from pydantic import Field

from app.models.enums import NoteSourceType, NoteType
from app.schemas.analysis import AIMetadata
from app.schemas.common import BaseSchema


class NoteGenerateRequest(BaseSchema):
    topic: str | None = Field(default=None, max_length=200)
    analysis_id: str | None = None
    topics: list[str] = Field(default_factory=list, max_length=20)
    title: str | None = Field(default=None, max_length=200)
    subject: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, max_length=100)
    frequency: int | None = Field(default=None, ge=1)
    regenerate: bool = False


class TopicNoteGenerateRequest(BaseSchema):
    topic: str = Field(min_length=1, max_length=200)
    analysis_id: str | None = None
    subject: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, max_length=100)
    frequency: int | None = Field(default=None, ge=1)
    regenerate: bool = False


class GeneratedNoteResponse(BaseSchema):
    id: str
    user_id: str
    topic: str
    notes: str
    summary: str | None = None
    subject: str | None = None
    unit: str | None = None
    frequency: int | None = None
    analysis_id: str | None = None
    is_saved: bool = False
    cached: bool = False
    ai_metadata: AIMetadata | None = None
    generated_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TopicCacheStatusResponse(BaseSchema):
    topic: str
    has_notes: bool
    note_id: str | None = None


class NoteSimplifyRequest(BaseSchema):
    document_id: str | None = None
    text: str | None = Field(default=None, max_length=50000)
    title: str | None = Field(default=None, max_length=200)


class NoteUpdateRequest(BaseSchema):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    is_favorite: bool | None = None


class NoteResponse(BaseSchema):
    id: str
    user_id: str
    title: str
    type: NoteType
    source_type: NoteSourceType | None = None
    source_id: str | None = None
    content: str
    summary: str | None = None
    topics: list[str] = []
    is_favorite: bool = False
    ai_metadata: AIMetadata | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
