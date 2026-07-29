"""Quality validation and deduplication for ExamBuddy exam notes."""

from __future__ import annotations

import re
from typing import Any

from app.services.ai.notes_sanitizer import is_placeholder_notes
from app.services.notes_engine.markdown_formatter import _as_bullets, _as_text, _qa_pairs, _resolve
from app.services.notes_engine.schema import (
    SCHEMA_CONTENT_FIELDS,
    SCHEMA_QA_LIST_FIELDS,
    SCHEMA_STRING_FIELDS,
    SCHEMA_STRING_LIST_FIELDS,
)

_NORMALIZE = re.compile(r"[^a-z0-9\s]+")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", _NORMALIZE.sub(" ", (text or "").lower())).strip()


def _dedupe_bullets(items: list[str], *, seen: set[str] | None = None) -> list[str]:
    out: list[str] = []
    local_seen = seen if seen is not None else set()
    for item in items:
        key = _norm(item)
        if not key or len(key) < 8:
            if key and key not in local_seen:
                local_seen.add(key)
                out.append(item.strip())
            continue
        duplicate = False
        for existing in list(local_seen):
            if key == existing or (key in existing and len(key) > 20) or (existing in key and len(existing) > 20):
                duplicate = True
                break
        if duplicate:
            continue
        local_seen.add(key)
        out.append(item.strip())
    return out


def deduplicate_structured_notes(data: dict[str, Any]) -> dict[str, Any]:
    """Remove repeated bullets across sections."""
    result = dict(data)
    global_seen: set[str] = set()

    bullet_keys = (
        "keyConcepts",
        "advantages",
        "disadvantages",
        "applications",
        "commonMistakes",
        "revisionSummary",
        "revisionSheet",
        "thirtySecondRevision",
        "keyTakeaways",
        "importantExamPoints",
        "characteristics",
        "keywords",
        "formulae",
    )
    for key in bullet_keys:
        bullets = _as_bullets(result.get(key))
        if not bullets:
            continue
        section_seen: set[str] = set()
        cleaned = _dedupe_bullets(bullets, seen=section_seen)
        final: list[str] = []
        for bullet in cleaned:
            key_n = _norm(bullet)
            if key_n in global_seen:
                continue
            if any(key_n in g and len(key_n) > 24 for g in global_seen):
                continue
            final.append(bullet)
            global_seen.add(key_n)
        if key in ("revisionSummary", "revisionSheet", "thirtySecondRevision"):
            final = final[:12]
        result[key] = final

    for key in (
        "vivaQuestions",
        "interviewQuestions",
        "frequentlyAskedQuestions",
    ):
        pairs = _qa_pairs(result.get(key))
        uniq: list[dict[str, str]] = []
        qseen: set[str] = set()
        for q, a in pairs:
            qn = _norm(q)
            if not qn or qn in qseen:
                continue
            qseen.add(qn)
            uniq.append({"question": q, "answer": a})
        if uniq:
            result[key] = uniq

    definition = _as_text(_resolve(result, "definition"))
    detailed = _as_text(_resolve(result, "detailedExplanation"))
    if definition and detailed and _norm(definition) in _norm(detailed):
        lines = [ln for ln in detailed.splitlines() if _norm(ln) != _norm(definition)]
        cleaned = "\n".join(lines).strip()
        if result.get("detailedExplanation") is not None:
            result["detailedExplanation"] = cleaned
        elif result.get("deepDive") is not None:
            result["deepDive"] = cleaned

    return result


# Defensive cap on any single free-text field. The model occasionally ignores
# prompt length guidance and rambles for tens of thousands of characters on
# one open-ended field (observed on "working"/"introduction" for well-known
# topics), which produces unusable notes and risks truncating later JSON
# fields against maxOutputTokens. This is enforced in code, independent of
# prompt compliance.
_MAX_FIELD_CHARS = 2200
_MAX_LIST_ITEMS = 15
_MAX_LIST_ITEM_CHARS = 600


def _cap_text(value: str) -> str:
    if len(value) <= _MAX_FIELD_CHARS:
        return value
    truncated = value[:_MAX_FIELD_CHARS].rsplit(" ", 1)[0].rstrip(".,;: ")
    return truncated + "…"


def cap_field_lengths(data: dict[str, Any]) -> dict[str, Any]:
    """Hard-cap oversized string/list fields so a single runaway field can
    never blow up the rendered notes or crowd out other sections."""
    from app.services.notes_engine.schema import SCHEMA_STRING_FIELDS, SCHEMA_STRING_LIST_FIELDS

    result = dict(data)
    for key in list(result.keys()):
        value = result[key]
        if key in SCHEMA_STRING_FIELDS and isinstance(value, str) and value:
            result[key] = _cap_text(value)
        elif key in SCHEMA_STRING_LIST_FIELDS and isinstance(value, list):
            capped_items = []
            for item in value[:_MAX_LIST_ITEMS]:
                if isinstance(item, str) and len(item) > _MAX_LIST_ITEM_CHARS:
                    capped_items.append(item[:_MAX_LIST_ITEM_CHARS].rstrip() + "…")
                else:
                    capped_items.append(item)
            result[key] = capped_items
    return result


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
    """Schema invalid after repair — surface as structured backend error."""

    def __init__(
        self,
        message: str = "AI returned invalid notes JSON after repair",
        *,
        details: list[Any] | None = None,
    ) -> None:
        super().__init__(message, code="NOTES_SCHEMA_INVALID", details=details)


def _is_nonempty_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def validate_exam_notes_schema(data: Any) -> None:
    """Validate LLM JSON against the ExamBuddy notes schema before formatting.

    Raises NotesValidationError with code NOTES_SCHEMA_INVALID on structural
    failures. UNKNOWN_TOPIC payloads are accepted as schema-valid.
    """
    if not isinstance(data, dict):
        raise NotesValidationError(
            "Notes JSON must be an object",
            code="NOTES_SCHEMA_INVALID",
            details=[{"field": "$", "error": "expected object"}],
        )
    if not data:
        raise NotesValidationError(
            "Notes JSON is empty",
            code="NOTES_SCHEMA_INVALID",
            details=[{"field": "$", "error": "empty object"}],
        )

    status = str(data.get("status") or "").strip().upper()
    topic_val = str(data.get("topic") or "").strip().upper()
    if status == "UNKNOWN_TOPIC" or topic_val == "UNKNOWN_TOPIC":
        return

    errors: list[dict[str, str]] = []

    for key, value in data.items():
        if value is None:
            continue
        if key in SCHEMA_STRING_FIELDS and not isinstance(value, str):
            # Allow numbers coerced later; reject lists/dicts for scalar text.
            if isinstance(value, (list, dict, bool)):
                errors.append({"field": key, "error": "expected string"})
        elif key in SCHEMA_STRING_LIST_FIELDS:
            if not isinstance(value, list):
                if not isinstance(value, str):
                    errors.append({"field": key, "error": "expected string array"})
            else:
                for i, item in enumerate(value):
                    if item is not None and not isinstance(item, (str, int, float)):
                        errors.append({"field": f"{key}[{i}]", "error": "expected string"})
        elif key in SCHEMA_QA_LIST_FIELDS:
            if not isinstance(value, list):
                errors.append({"field": key, "error": "expected FAQ array"})
            else:
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        q = item.get("question")
                        a = item.get("answer")
                        if q is not None and not isinstance(q, str):
                            errors.append({"field": f"{key}[{i}].question", "error": "expected string"})
                        if a is not None and not isinstance(a, str):
                            errors.append({"field": f"{key}[{i}].answer", "error": "expected string"})
                    elif not isinstance(item, str):
                        errors.append({"field": f"{key}[{i}]", "error": "expected object or string"})
        elif key == "comparison" and value is not None and not isinstance(value, (dict, str)):
            errors.append({"field": "comparison", "error": "expected object or string"})

    has_content = any(
        _is_nonempty_value(data.get(field))
        or _is_nonempty_value(data.get(alias))
        for field in SCHEMA_CONTENT_FIELDS
        for alias in (field, "whatIsIt", "howItWorks", "revisionSheet")
    )
    # Also accept common alias presence via resolve-like checks.
    if not has_content:
        has_content = bool(
            _as_text(data.get("definition") or data.get("whatIsIt"))
            or _as_text(data.get("working") or data.get("howItWorks"))
            or _as_text(data.get("notes"))
            or _as_bullets(data.get("revisionSummary") or data.get("revisionSheet"))
            or _as_text(data.get("twoMarkAnswer"))
        )
    if not has_content:
        errors.append({"field": "$", "error": "no content sections present"})

    if errors:
        raise NotesValidationError(
            "Notes JSON failed ExamBuddy schema validation",
            code="NOTES_SCHEMA_INVALID",
            details=errors,
        )


def validate_exam_notes(data: dict[str, Any], *, markdown: str) -> None:
    """Fail fast on empty / placeholder / too-thin exam notes."""
    if not markdown or len(markdown.strip()) < 120:
        raise NotesValidationError(
            "Notes markdown too short",
            code="NOTES_QUALITY_GATE",
            details=[{"field": "markdown", "error": "too short"}],
        )
    if is_placeholder_notes(markdown):
        raise NotesValidationError(
            "Notes contain instruction placeholders",
            code="NOTES_QUALITY_GATE",
            details=[{"field": "markdown", "error": "placeholder content"}],
        )

    definition = _as_text(data.get("definition") or data.get("whatIsIt"))
    has_definition = bool(definition) or "## Definition" in markdown or "## 1. What is it?" in markdown
    if not has_definition:
        raise NotesValidationError(
            "Missing definition section",
            code="NOTES_QUALITY_GATE",
            details=[{"field": "definition", "error": "missing"}],
        )

    has_revision = any(
        [
            _as_bullets(data.get("revisionSummary")),
            _as_bullets(data.get("revisionSheet")),
            _as_bullets(data.get("keywords")),
            _as_text(data.get("twoMarkAnswer")),
            _as_bullets(data.get("thirtySecondRevision")),
            "## Revision Summary" in markdown,
            "## 2-Mark Answer" in markdown,
            "## Keywords" in markdown,
        ]
    )
    if not has_revision:
        raise NotesValidationError(
            "Missing revision / mark-wise answer sections",
            code="NOTES_QUALITY_GATE",
            details=[{"field": "revisionSummary", "error": "missing"}],
        )


_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def count_words(markdown: str) -> int:
    """Approximate word count of rendered markdown (used for the 2000-5000 word gate)."""
    return len(_WORD_RE.findall(markdown or ""))


def validate_section_payload(section_id: str, data: Any) -> None:
    """Validate ONE section batch's JSON payload before merging it into the document.

    Raises NotesValidationError(code="SECTION_SCHEMA_INVALID") on missing/thin
    fields so the pipeline can attempt a single scoped repair for that batch only.
    """
    from app.services.notes_engine.schema import SECTION_VALIDATION_RULES

    if not isinstance(data, dict) or not data:
        raise NotesValidationError(
            f"Section '{section_id}' returned empty or non-object JSON",
            code="SECTION_SCHEMA_INVALID",
            details=[{"section": section_id, "field": "$", "error": "empty or non-object"}],
        )

    rules = SECTION_VALIDATION_RULES.get(section_id, {})
    errors: list[dict[str, str]] = []

    for field, rule in rules.items():
        value = data.get(field)
        kind = rule.get("kind")
        min_items = rule.get("min_items") or 1

        if kind == "text":
            if not _as_text(value):
                errors.append({"section": section_id, "field": field, "error": "missing"})
        elif kind == "list":
            items = value if isinstance(value, list) else ([value] if _is_nonempty_value(value) else [])
            if len(items) < min_items:
                errors.append(
                    {
                        "section": section_id,
                        "field": field,
                        "error": f"expected >= {min_items} items, got {len(items)}",
                    }
                )
        elif kind == "qa_list":
            pairs = _qa_pairs(value)
            if len(pairs) < min_items:
                errors.append(
                    {
                        "section": section_id,
                        "field": field,
                        "error": f"expected >= {min_items} Q&A pairs, got {len(pairs)}",
                    }
                )

    if errors:
        raise NotesValidationError(
            f"Section '{section_id}' failed content validation",
            code="SECTION_SCHEMA_INVALID",
            details=errors,
        )


def validate_final_notes(markdown: str, structured: dict[str, Any], *, word_count: int) -> None:
    """Fail fast on a thin, "summary-style", or structurally incomplete final document."""
    from app.services.notes_engine.schema import MIN_WORD_COUNT_SOFT, REQUIRED_HEADING_KEYWORDS

    _ = structured
    if not markdown or len(markdown.strip()) < 800:
        raise NotesValidationError(
            "Merged notes markdown too short",
            code="NOTES_QUALITY_GATE",
            details=[{"field": "markdown", "error": "too short"}],
        )
    if is_placeholder_notes(markdown):
        raise NotesValidationError(
            "Notes contain instruction placeholders",
            code="NOTES_QUALITY_GATE",
            details=[{"field": "markdown", "error": "placeholder content"}],
        )

    lowered = markdown.lower()
    missing = [kw for kw in REQUIRED_HEADING_KEYWORDS if kw not in lowered]
    if missing:
        raise NotesValidationError(
            "Final notes missing required headings",
            code="NOTES_MISSING_HEADINGS",
            details=[{"field": "headings", "missing": missing}],
        )

    if word_count < MIN_WORD_COUNT_SOFT:
        raise NotesValidationError(
            f"Final notes too short ({word_count} words, need >= {MIN_WORD_COUNT_SOFT})",
            code="NOTES_TOO_SHORT",
            details=[{"field": "word_count", "value": word_count, "min": MIN_WORD_COUNT_SOFT}],
        )


def score_notes_quality(data: dict[str, Any], markdown: str) -> dict[str, Any]:
    """Lightweight quality metrics for logging/metadata."""
    return {
        "chars": len(markdown or ""),
        "has_definition": bool(_as_text(data.get("definition") or data.get("whatIsIt"))),
        "has_diagram": bool(_as_text(data.get("diagram"))),
        "has_mark_answers": bool(
            _as_text(data.get("twoMarkAnswer"))
            or _as_text(data.get("fiveMarkAnswer"))
            or _as_text(data.get("tenMarkAnswer"))
        ),
        "faq_count": len(_qa_pairs(data.get("frequentlyAskedQuestions") or data.get("examQuestions"))),
        "viva_count": len(_qa_pairs(data.get("vivaQuestions"))),
        "interview_count": len(_qa_pairs(data.get("interviewQuestions"))),
        "has_table": bool(data.get("comparison") or data.get("table")),
        "revision_bullets": len(
            _as_bullets(data.get("revisionSummary") or data.get("revisionSheet") or data.get("summary"))
        ),
        "topic_type": _as_text(data.get("topicType") or data.get("category")),
    }
