"""Quality validation and deduplication for ExamBuddy exam notes."""

from __future__ import annotations

import re
from typing import Any

from app.services.ai.notes_sanitizer import is_placeholder_notes
from app.services.notes_engine.markdown_formatter import _as_bullets, _as_text, _qa_pairs, _resolve

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


class NotesValidationError(ValueError):
    """Raised when generated notes fail quality gates."""


def validate_exam_notes(data: dict[str, Any], *, markdown: str) -> None:
    """Fail fast on empty / placeholder / too-thin exam notes."""
    if not markdown or len(markdown.strip()) < 120:
        raise NotesValidationError("Notes markdown too short")
    if is_placeholder_notes(markdown):
        raise NotesValidationError("Notes contain instruction placeholders")

    definition = _as_text(data.get("definition") or data.get("whatIsIt"))
    has_definition = bool(definition) or "## Definition" in markdown or "## 1. What is it?" in markdown
    if not has_definition:
        raise NotesValidationError("Missing definition section")

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
        raise NotesValidationError("Missing revision / mark-wise answer sections")


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
