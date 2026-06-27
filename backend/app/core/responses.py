from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[Any] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    has_next: bool


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    pagination: PaginationMeta
    message: str | None = None


def success_response(data: Any, message: str | None = None) -> dict[str, Any]:
    return {"success": True, "data": data, "message": message}


def paginated_response(
    data: list[Any],
    page: int,
    limit: int,
    total: int,
    message: str | None = None,
) -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "has_next": page * limit < total,
        },
        "message": message,
    }


def error_response(code: str, message: str, details: list[Any] | None = None) -> dict[str, Any]:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        },
    }
