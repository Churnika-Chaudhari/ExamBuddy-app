from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MessageResponse(BaseSchema):
    message: str


class PaginationParams(BaseSchema):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class IDResponse(BaseSchema):
    id: str


class TimestampMixin(BaseSchema):
    created_at: datetime | None = None
    updated_at: datetime | None = None


def object_id_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
