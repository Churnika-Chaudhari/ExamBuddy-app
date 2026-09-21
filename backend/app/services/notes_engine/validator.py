"""Validation gates for ExamBuddy concise exam notes (v40).

Two gates:
  1. `validate_concise_payload` — structural: all seven sections present with
     enough real content. Failure triggers ONE scoped repair call.
  2. `validate_final_notes` — document-level: every heading rendered, no
     placeholder/prompt-leak text, word count inside the soft band.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.ai.notes_sanitizer import is_placeholder_notes
from app.services.notes_engine.markdown_formatter import _as_bullets, _as_text
from app.services.notes_engine.schema import (
    LIST_FIELDS,
    MAX_WORD_COUNT_SOFT,
    MIN_DEFINITION_CHARS,
    MIN_EXAMPLE_CHARS,
    MIN_LIST_ITEM_CHARS,
    MIN_WORD_COUNT_SOFT,
    SECTION_HEADINGS,
    SECTION_ITEM_LIMITS,
    SECTION_ORDER,
    TARGET_WORD_COUNT_MAX,
    TARGET_WORD_COUNT_MIN,
)

_WORD_RE = re.compile(r"[A-Za-z0-9']+")

# Content that means the model dodged the section instead of writing it.
_STUB_VALUES = frozenset(
    {"n/a", "na", "none", "not applicable", "not available", "nil", "-", "--", "unknown", "tbd"}
)

# Banned meta/PYQ phrasing the product spec forbids outright. Checked against
# the rendered markdown so it catches leakage from any field.
_BANNED_PHRASES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("pyq_reference", re.compile(r"\b(previous year|pyq|question paper|exam paper)\b", re.I)),
    ("marks_reference", re.compile(r"\b\d+\s*marks?\b", re.I)),
    ("ai_reference", re.compile(r"\b(as an ai|language model|exambuddy|these notes were)\b", re.I)),
    ("importance_claim", re.compile(r"\b(frequently asked|commonly asked|is (an )?important topic|scoring topic)\b", re.I)),
)

# Topic lines that were copied as a question instead of a concept.
_QUESTION_TOPIC = re.compile(
    r"^#\s*(explain|discuss|describe|define|what\s+is|what\s+are|write\s+a?\s*short\s+note)\b",
    re.I,
)


class NotesValidationError(ValueError):
    """Raised when generated notes fail schema or quality gates."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "NOTES_VALIDATION_ERROR",
        details: list[Any] | None = None,
    ) -> None:
        self.code = code
        self.details = details or []
        super().__init__(message)


class NotesSchemaError(NotesValidationError):
    """Schema still invalid after the repair attempt."""

    def __init__(
        self,
        message: str = "AI returned invalid notes JSON after repair",
        *,
        details: list[Any] | None = None,
    ) -> None:
        super().__init__(message, code="NOTES_SCHEMA_INVALID", details=details)


def count_words(markdown: str) -> int:
    """Approximate word count of rendered markdown (300-600 word target)."""
    return len(_WORD_RE.findall(markdown or ""))


def _is_stub(text: str) -> bool:
    return text.strip().strip(".").lower() in _STUB_VALUES


def validate_concise_payload(data: Any, *, topic: str = "") -> None:
    """Require all seven sections with real, non-stub content.

    Raises NotesValidationError(code="NOTES_SCHEMA_INVALID") listing every
    problem at once so a single repair call can fix them all.
    """
    if not isinstance(data, dict) or not data:
        raise NotesValidationError(
            "Notes JSON is empty or not an object",
            code="NOTES_SCHEMA_INVALID",
            details=[{"field": "$", "error": "empty or non-object"}],
        )

    errors: list[dict[str, Any]] = []

    for field, heading in SECTION_ORDER:
        if field in LIST_FIELDS:
            items = [b for b in _as_bullets(data.get(field)) if b and not _is_stub(b)]
            min_items = SECTION_ITEM_LIMITS[field][0]
            if len(items) < min_items:
                errors.append(
                    {
                        "field": field,
                        "section": heading,
                        "error": f"expected at least {min_items} items, got {len(items)}",
                    }
                )
                continue
            thin = [i for i in items if len(i) < MIN_LIST_ITEM_CHARS]
            if len(thin) > len(items) // 2:
                errors.append(
                    {"field": field, "section": heading, "error": "items are too short to be useful"}
                )
            continue

        text = _as_text(data.get(field))
        min_chars = MIN_DEFINITION_CHARS if field == "definition" else MIN_EXAMPLE_CHARS
        if not text or _is_stub(text):
            errors.append({"field": field, "section": heading, "error": "missing"})
        elif len(text) < min_chars:
            errors.append(
                {
                    "field": field,
                    "section": heading,
                    "error": f"too short ({len(text)} chars, need >= {min_chars})",
                }
            )

    if errors:
        raise NotesValidationError(
            f"Concise notes JSON for '{topic or 'topic'}' failed section validation",
            code="NOTES_SCHEMA_INVALID",
            details=errors,
        )


def word_count_status(word_count: int) -> str:
    """Where the document sits relative to the 300-600 word target."""
    if word_count < TARGET_WORD_COUNT_MIN:
        return "under_target"
    if word_count > TARGET_WORD_COUNT_MAX:
        return "over_target"
    return "on_target"


def validate_final_notes(markdown: str, structured: dict[str, Any], *, word_count: int) -> None:
    """Document-level gate on the rendered markdown.

    Being over the word band raises too, so the pipeline can ask for a shorter
    rewrite — but the pipeline accepts an over-long-yet-otherwise-valid note
    rather than failing the request outright (see ConciseNotesPipeline).
    """
    _ = structured

    if not markdown or len(markdown.strip()) < 300:
        raise NotesValidationError(
            "Rendered notes are too short",
            code="NOTES_QUALITY_GATE",
            details=[{"field": "markdown", "error": "too short"}],
        )
    if is_placeholder_notes(markdown):
        raise NotesValidationError(
            "Notes contain instruction placeholders",
            code="NOTES_QUALITY_GATE",
            details=[{"field": "markdown", "error": "placeholder content"}],
        )

    missing = [h for h in SECTION_HEADINGS if f"## {h}" not in markdown]
    if missing:
        raise NotesValidationError(
            "Notes are missing required sections",
            code="NOTES_MISSING_HEADINGS",
            details=[{"field": "headings", "missing": missing}],
        )

    first_line = markdown.strip().splitlines()[0] if markdown.strip() else ""
    if _QUESTION_TOPIC.match(first_line):
        raise NotesValidationError(
            "Topic was treated as an exam question",
            code="NOTES_QUALITY_GATE",
            details=[{"field": "topic", "error": "question phrasing"}],
        )

    leaked = [name for name, pattern in _BANNED_PHRASES if pattern.search(markdown)]
    if leaked:
        raise NotesValidationError(
            "Notes contain forbidden meta/PYQ references",
            code="NOTES_QUALITY_GATE",
            details=[{"field": "markdown", "banned": leaked}],
        )

    if word_count < MIN_WORD_COUNT_SOFT:
        raise NotesValidationError(
            f"Notes too short ({word_count} words, need >= {MIN_WORD_COUNT_SOFT})",
            code="NOTES_TOO_SHORT",
            details=[{"field": "word_count", "value": word_count, "min": MIN_WORD_COUNT_SOFT}],
        )
    if word_count > MAX_WORD_COUNT_SOFT:
        raise NotesValidationError(
            f"Notes too long ({word_count} words, max {MAX_WORD_COUNT_SOFT})",
            code="NOTES_TOO_LONG",
            details=[{"field": "word_count", "value": word_count, "max": MAX_WORD_COUNT_SOFT}],
        )


def score_notes_quality(data: dict[str, Any], markdown: str) -> dict[str, Any]:
    """Lightweight metrics stored in ai_metadata for logging/debugging."""
    return {
        "chars": len(markdown or ""),
        "word_count": count_words(markdown),
        "definition_chars": len(_as_text(data.get("definition"))),
        "working_steps": len(_as_bullets(data.get("working"))),
        "advantages": len(_as_bullets(data.get("advantages"))),
        "disadvantages": len(_as_bullets(data.get("disadvantages"))),
        "applications": len(_as_bullets(data.get("applications"))),
        "quick_revision": len(_as_bullets(data.get("quick_revision"))),
        "has_example": bool(_as_text(data.get("example"))),
    }
