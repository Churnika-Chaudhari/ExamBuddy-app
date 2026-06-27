from datetime import datetime

from pydantic import Field

from app.models.enums import DocumentCategory, FileType, ProcessingStatus
from app.schemas.common import BaseSchema


class DocumentUpdateRequest(BaseSchema):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    subject: str | None = Field(default=None, max_length=100)
    exam_year: int | None = Field(default=None, ge=1900, le=2100)
    category: DocumentCategory | None = None
    tags: list[str] | None = None


class DocumentResponse(BaseSchema):
    id: str
    user_id: str
    title: str
    description: str | None = None
    category: DocumentCategory
    subject: str | None = None
    exam_year: int | None = None
    file_type: FileType
    file_url: str
    file_public_id: str
    file_size_bytes: int | None = None
    page_count: int | None = None
    extracted_text: str | None = None
    status: ProcessingStatus
    error_message: str | None = None
    tags: list[str] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentStatusResponse(BaseSchema):
    id: str
    status: ProcessingStatus
    error_message: str | None = None


class DocumentUploadResponse(BaseSchema):
    document: DocumentResponse
    message: str = "Document uploaded successfully. Text extraction in progress."
