from typing import Any


class AppException(Exception):
    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 400,
        details: list[Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", details: list[Any] | None = None) -> None:
        super().__init__(message=message, code="NOT_FOUND", status_code=404, details=details)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized", details: list[Any] | None = None) -> None:
        super().__init__(message=message, code="UNAUTHORIZED", status_code=401, details=details)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Forbidden", details: list[Any] | None = None) -> None:
        super().__init__(message=message, code="FORBIDDEN", status_code=403, details=details)


class ConflictError(AppException):
    def __init__(self, message: str = "Conflict", details: list[Any] | None = None) -> None:
        super().__init__(message=message, code="CONFLICT", status_code=409, details=details)


class ValidationAppError(AppException):
    def __init__(self, message: str = "Validation error", details: list[Any] | None = None) -> None:
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=422, details=details)


class ExternalServiceError(AppException):
    def __init__(self, message: str = "External service error", details: list[Any] | None = None) -> None:
        super().__init__(message=message, code="EXTERNAL_SERVICE_ERROR", status_code=502, details=details)
