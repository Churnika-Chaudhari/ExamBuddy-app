import re
from typing import Any, Iterator

# Matches Gemini/OpenAI 429 quota-exhaustion errors regardless of where in an
# exception's __cause__ chain the real provider message ended up.
RATE_LIMIT_PATTERN = re.compile(r"\b429\b|resource_exhausted|rate.?limit|quota", re.I)
_RETRY_DELAY_PATTERN = re.compile(r"retry in\s*([\d.]+)\s*s", re.I)


def iter_exception_chain(exc: BaseException | None) -> Iterator[BaseException]:
    """
    Walk exc, exc.__cause__, exc.__cause__.__cause__, ... (cycle-safe).

    Falls back to __context__ when __cause__ is unset — an exception raised
    inside an `except:` block without an explicit `raise ... from ...` still
    carries the original error on __context__, and that's often where the
    real Gemini 429/quota text lives.
    """
    seen: set[int] = set()
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def describe_exception_chain(exc: BaseException | None, *, max_len: int = 500) -> str:
    """
    Human-readable summary of an exception AND its __cause__ chain.

    Wrapper exceptions (e.g. ExternalServiceError("... failed for all
    providers")) intentionally chain the real provider error via `raise ...
    from last_exc`, but that real message (the actual 429/quota text) is easy
    to lose if callers only look at str(exc). This walks the whole chain so
    the underlying cause is never silently swallowed.
    """
    parts: list[str] = []
    for err in iter_exception_chain(exc):
        text = str(err).strip()
        if text and text not in parts:
            parts.append(text)
    if not parts:
        return "Unknown error"
    return " | caused by: ".join(parts)[:max_len]


def is_rate_limit_error(exc: BaseException | None) -> bool:
    """True if exc OR any exception in its __cause__ chain looks like a 429/quota error."""
    return any(RATE_LIMIT_PATTERN.search(str(err)) for err in iter_exception_chain(exc))


def suggested_retry_delay_seconds(exc: BaseException | None) -> float | None:
    """Best-effort parse of a provider-suggested 'retry in Xs' delay from the exception chain."""
    for err in iter_exception_chain(exc):
        match = _RETRY_DELAY_PATTERN.search(str(err))
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None


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
