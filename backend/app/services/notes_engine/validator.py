"""Quality validation and deduplication for exam notes."""

from __future__ import annotations

import re
from typing import Any

from app.services.ai.notes_sanitizer import is_placeholder_notes
from app.services.notes_engine.markdown_formatter import _as_bullets, _as_text, _qa_pairs

_NORMALIZE = re.compile(r"[^a-z0-9\s]+")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", _NORMALIZE.sub(" ", (text or "").lower())).strip()


def _dedupe_bullets(items: list[str], *, seen: set[str] | None = None) -> list[str]:
    out: list[str] = []
    local_seen = seen if seen is not None else set()
    for item in items:
        key = _norm(item)
        if not key or len(key) < 8:
            # keep very short unique labels
            if key and key not in local_seen:
                local_seen.add(key)
                out.append(item.strip())
            continue
        # Near-duplicate if one contains the other heavily
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
    """Remove repeated bullets across sections; keep highest-value sections denser."""
    result = dict(data)
    global_seen: set[str] = set()

    for key in (
        "whyItMatters",
        "keyConcepts",
        "importantExamPoints",
        "commonMistakes",
        "examples",
        "thirtySecondRevision",
    ):
        bullets = _as_bullets(result.get(key))
        if not bullets:
            continue
        # Exam points / key concepts may share themes with revision — allow light overlap
        # by using a section-local set first, then register into global.
        section_seen: set[str] = set()
        cleaned = _dedupe_bullets(bullets, seen=section_seen)
        # Drop bullets already used almost verbatim in earlier sections
        final: list[str] = []
        for bullet in cleaned:
            key_n = _norm(bullet)
            if key_n in global_seen:
                continue
            # Soft global: skip if a longer earlier bullet contains this one
            if any(key_n in g and len(key_n) > 24 for g in global_seen):
                continue
            final.append(bullet)
            global_seen.add(key_n)
        if key == "whyItMatters":
            final = final[:3]
        if key == "thirtySecondRevision":
            final = final[:10]
        result[key] = final

    # Deduplicate FAQ / viva questions by question text
    for key in ("frequentlyAskedQuestions", "vivaQuestions"):
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

    definition = _as_text(result.get("definition"))
    detailed = _as_text(result.get("detailedExplanation"))
    if definition and detailed and _norm(definition) in _norm(detailed):
        # Strip leading duplicate definition paragraph from detailed explanation
        lines = [ln for ln in detailed.splitlines() if _norm(ln) != _norm(definition)]
        result["detailedExplanation"] = "\n".join(lines).strip()

    return result


class NotesValidationError(ValueError):
    """Raised when generated notes fail quality gates."""


def validate_exam_notes(data: dict[str, Any], *, markdown: str) -> None:
    """Fail fast on empty / placeholder / too-thin notes."""
    if not markdown or len(markdown.strip()) < 120:
        raise NotesValidationError("Notes markdown too short")
    if is_placeholder_notes(markdown):
        raise NotesValidationError("Notes contain instruction placeholders")
    if not _as_text(data.get("definition")) and "## Definition" not in markdown:
        raise NotesValidationError("Missing definition section")

    # Require at least one revision-oriented section
    has_revision = any(
        [
            _as_bullets(data.get("importantExamPoints")),
            _as_bullets(data.get("thirtySecondRevision")),
            _as_bullets(data.get("keyPoints")),
            "## Important Exam Points" in markdown,
            "## 30 Second Revision" in markdown,
        ]
    )
    if not has_revision:
        raise NotesValidationError("Missing exam revision sections")


def score_notes_quality(data: dict[str, Any], markdown: str) -> dict[str, Any]:
    """Lightweight quality metrics for logging/metadata."""
    return {
        "chars": len(markdown or ""),
        "has_definition": bool(_as_text(data.get("definition"))),
        "exam_points": len(_as_bullets(data.get("importantExamPoints") or data.get("keyPoints"))),
        "faq_count": len(_qa_pairs(data.get("frequentlyAskedQuestions") or data.get("examQuestions"))),
        "viva_count": len(_qa_pairs(data.get("vivaQuestions") or data.get("interviewQuestions"))),
        "has_table": bool(data.get("table") or data.get("comparison")),
        "has_memory_trick": bool(_as_text(data.get("memoryTrick") or data.get("mnemonic"))),
        "revision_bullets": len(
            _as_bullets(data.get("thirtySecondRevision") or data.get("summary"))
        ),
    }
