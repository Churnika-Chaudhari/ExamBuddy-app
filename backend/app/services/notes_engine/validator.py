"""Quality validation and deduplication for Professor Alex lecture notes."""

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
    """Remove repeated bullets across sections; keep lecture sections dense."""
    result = dict(data)
    global_seen: set[str] = set()

    bullet_keys = (
        "whyNeeded",
        "whyItMatters",
        "advantages",
        "disadvantages",
        "commonMistakes",
        "memoryTricks",
        "keyTakeaways",
        "importantExamPoints",
        "revisionSheet",
        "thirtySecondRevision",
        "examples",
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
        if key in ("whyNeeded", "whyItMatters"):
            final = final[:6]
        if key in ("revisionSheet", "thirtySecondRevision"):
            final = final[:15]
        if key in ("keyTakeaways", "importantExamPoints"):
            final = final[:12]
        result[key] = final

    for key in ("vivaQuestions", "frequentlyAskedQuestions", "interviewQuestions"):
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

    # Deduplicate nested examQuestions
    exam_q = result.get("examQuestions")
    if isinstance(exam_q, dict):
        cleaned_exam: dict[str, Any] = {}
        for nest_key in ("longAnswer", "shortAnswer", "long_answer", "short_answer"):
            pairs = _qa_pairs(exam_q.get(nest_key))
            if not pairs:
                continue
            uniq: list[dict[str, str]] = []
            qseen: set[str] = set()
            for q, a in pairs:
                qn = _norm(q)
                if not qn or qn in qseen:
                    continue
                qseen.add(qn)
                uniq.append({"question": q, "answer": a})
            if uniq:
                cleaned_exam[nest_key] = uniq
        if cleaned_exam:
            result["examQuestions"] = {**exam_q, **cleaned_exam}
    elif isinstance(exam_q, list):
        pairs = _qa_pairs(exam_q)
        uniq = []
        qseen = set()
        for q, a in pairs:
            qn = _norm(q)
            if not qn or qn in qseen:
                continue
            qseen.add(qn)
            uniq.append({"question": q, "answer": a})
        if uniq:
            result["examQuestions"] = uniq

    what = _as_text(_resolve(result, "whatIsIt") or result.get("definition"))
    deep = _as_text(result.get("deepDive") or result.get("detailedExplanation"))
    if what and deep and _norm(what) in _norm(deep):
        lines = [ln for ln in deep.splitlines() if _norm(ln) != _norm(what)]
        cleaned = "\n".join(lines).strip()
        if result.get("deepDive") is not None:
            result["deepDive"] = cleaned
        elif result.get("detailedExplanation") is not None:
            result["detailedExplanation"] = cleaned

    return result


class NotesValidationError(ValueError):
    """Raised when generated notes fail quality gates."""


def validate_exam_notes(data: dict[str, Any], *, markdown: str) -> None:
    """Fail fast on empty / placeholder / too-thin lecture notes."""
    if not markdown or len(markdown.strip()) < 120:
        raise NotesValidationError("Notes markdown too short")
    if is_placeholder_notes(markdown):
        raise NotesValidationError("Notes contain instruction placeholders")

    what = _as_text(data.get("whatIsIt") or data.get("definition"))
    has_what = bool(what) or "## 1. What is it?" in markdown or "## Definition" in markdown
    if not has_what:
        raise NotesValidationError("Missing What is it? / definition section")

    has_revision = any(
        [
            _as_bullets(data.get("revisionSheet")),
            _as_bullets(data.get("keyTakeaways")),
            _as_bullets(data.get("thirtySecondRevision")),
            _as_bullets(data.get("importantExamPoints")),
            "## 17. Revision Sheet" in markdown,
            "## 18. Key Takeaways" in markdown,
            "## Important Exam Points" in markdown,
            "## 30 Second Revision" in markdown,
        ]
    )
    if not has_revision:
        raise NotesValidationError("Missing revision / key takeaway sections")


def score_notes_quality(data: dict[str, Any], markdown: str) -> dict[str, Any]:
    """Lightweight quality metrics for logging/metadata."""
    exam_q = data.get("examQuestions")
    faq_count = 0
    if isinstance(exam_q, dict):
        faq_count = len(_qa_pairs(exam_q.get("longAnswer") or exam_q.get("long_answer"))) + len(
            _qa_pairs(exam_q.get("shortAnswer") or exam_q.get("short_answer"))
        )
    else:
        faq_count = len(_qa_pairs(exam_q or data.get("frequentlyAskedQuestions")))

    return {
        "chars": len(markdown or ""),
        "has_what_is_it": bool(_as_text(data.get("whatIsIt") or data.get("definition"))),
        "has_analogy": bool(_as_text(data.get("realLifeAnalogy") or data.get("analogy"))),
        "has_diagram": bool(_as_text(data.get("diagram"))),
        "takeaway_count": len(
            _as_bullets(data.get("keyTakeaways") or data.get("importantExamPoints") or data.get("keyPoints"))
        ),
        "faq_count": faq_count,
        "viva_count": len(_qa_pairs(data.get("vivaQuestions") or data.get("interviewQuestions"))),
        "mcq_count": len(data.get("mcqs") or []) if isinstance(data.get("mcqs"), list) else 0,
        "has_table": bool(data.get("comparison") or data.get("table")),
        "has_memory_trick": bool(
            _as_bullets(data.get("memoryTricks"))
            or _as_text(data.get("memoryTrick") or data.get("mnemonic"))
        ),
        "revision_bullets": len(
            _as_bullets(data.get("revisionSheet") or data.get("thirtySecondRevision") or data.get("summary"))
        ),
    }
