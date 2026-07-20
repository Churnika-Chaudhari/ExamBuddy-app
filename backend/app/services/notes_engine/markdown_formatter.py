"""Markdown formatter for exam-oriented structured notes."""

from __future__ import annotations

from typing import Any

from app.services.ai.notes_sanitizer import sanitize_note_text
from app.services.notes_engine.schema import FIELD_ALIASES


def _first_key(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        return value
    return None


def _resolve(data: dict[str, Any], canonical: str) -> Any:
    aliases = FIELD_ALIASES.get(canonical, (canonical,))
    return _first_key(data, *aliases, canonical)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        parts = [_as_text(item) for item in value]
        return "\n".join(p for p in parts if p)
    if isinstance(value, dict):
        for key in ("text", "description", "content", "value"):
            if value.get(key):
                return str(value[key]).strip()
    return str(value).strip()


def _as_bullets(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        lines = [ln.strip().lstrip("-•* ").strip() for ln in value.splitlines() if ln.strip()]
        return lines
    if isinstance(value, list):
        bullets: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                bullets.append(item.strip())
            elif isinstance(item, dict):
                name = _as_text(item.get("name") or item.get("title") or item.get("concept"))
                desc = _as_text(
                    item.get("description")
                    or item.get("detail")
                    or item.get("explanation")
                    or item.get("text")
                )
                if name and desc:
                    bullets.append(f"**{name}** — {desc}")
                elif name or desc:
                    bullets.append(name or desc)
        return bullets
    text = _as_text(value)
    return [text] if text else []


def _qa_pairs(value: Any) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                q = _as_text(item.get("question") or item.get("q"))
                a = _as_text(item.get("answer") or item.get("a"))
                if q:
                    pairs.append((q, a))
            elif isinstance(item, str) and item.strip():
                pairs.append((item.strip(), ""))
    elif isinstance(value, str) and value.strip():
        pairs.append((value.strip(), ""))
    return pairs


def _append_section(lines: list[str], title: str, content: Any) -> None:
    text = _as_text(content)
    if not text:
        return
    lines.extend([f"## {title}", text, ""])


def _append_bullets(lines: list[str], title: str, content: Any, *, limit: int | None = None) -> None:
    bullets = _as_bullets(content)
    if limit is not None:
        bullets = bullets[:limit]
    if not bullets:
        return
    lines.append(f"## {title}")
    lines.extend(f"- {b}" for b in bullets)
    lines.append("")


def _append_qa(lines: list[str], title: str, content: Any) -> None:
    pairs = _qa_pairs(content)
    if not pairs:
        return
    lines.append(f"## {title}")
    for idx, (question, answer) in enumerate(pairs, start=1):
        lines.append(f"### Q{idx}. {question}")
        if answer:
            lines.append(f"**Answer:** {answer}")
        lines.append("")


def _append_table(lines: list[str], table: Any) -> None:
    if not table:
        return

    # Legacy comparison object support
    if isinstance(table, dict) and (table.get("compareWith") or table.get("left")):
        left = _as_text(table.get("left") or "A")
        right = _as_text(table.get("compareWith") or table.get("right") or "B")
        rows = table.get("table") or table.get("rows") or []
        lines.append(f"## Table: {left} vs {right}")
        lines.append(f"| Aspect | {left} | {right} |")
        lines.append("|---|---|---|")
        for row in rows:
            if isinstance(row, dict):
                aspect = _as_text(row.get("aspect") or row.get("feature") or row.get("point"))
                lv = _as_text(row.get("leftValue") or row.get("left") or row.get("a"))
                rv = _as_text(row.get("rightValue") or row.get("right") or row.get("b"))
                if aspect:
                    lines.append(f"| {aspect} | {lv} | {rv} |")
            elif isinstance(row, (list, tuple)) and len(row) >= 3:
                lines.append(f"| {_as_text(row[0])} | {_as_text(row[1])} | {_as_text(row[2])} |")
        lines.append("")
        return

    if isinstance(table, str):
        text = table.strip()
        if text:
            lines.extend(["## Table", text, ""])
        return

    if not isinstance(table, dict):
        return

    title = _as_text(table.get("title") or "Table")
    headers = table.get("headers") or ["Aspect", "A", "B"]
    rows = table.get("rows") or []
    if not isinstance(headers, list) or not headers:
        return
    header_cells = [_as_text(h) for h in headers]
    lines.append(f"## Table: {title}" if title != "Table" else "## Table")
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append("|" + "|".join(["---"] * len(header_cells)) + "|")
    for row in rows:
        if isinstance(row, dict):
            cells = [_as_text(row.get(h, "")) for h in headers]
        elif isinstance(row, (list, tuple)):
            cells = [_as_text(c) for c in row[: len(header_cells)]]
            while len(cells) < len(header_cells):
                cells.append("")
        else:
            continue
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")


def format_exam_notes_markdown(data: dict[str, Any]) -> str:
    """Render exam-notes JSON into revision-friendly markdown."""
    topic = _as_text(data.get("topic") or data.get("title") or "Study Topic")
    lines: list[str] = [f"# {topic}", ""]

    _append_section(lines, "Definition", data.get("definition"))
    _append_bullets(lines, "Why It Matters", _resolve(data, "whyItMatters"), limit=3)
    _append_bullets(lines, "Key Concepts", _resolve(data, "keyConcepts"))
    _append_section(lines, "Detailed Explanation", _resolve(data, "detailedExplanation"))
    _append_section(lines, "Diagram", data.get("diagram"))
    _append_table(lines, _resolve(data, "table"))
    _append_bullets(lines, "Examples", _resolve(data, "examples"))
    _append_section(lines, "Memory Trick", _resolve(data, "memoryTrick"))
    _append_bullets(lines, "Important Exam Points ⭐⭐⭐", _resolve(data, "importantExamPoints"))
    _append_bullets(lines, "Common Mistakes", _resolve(data, "commonMistakes"))
    _append_qa(lines, "Frequently Asked Questions", _resolve(data, "frequentlyAskedQuestions"))
    _append_qa(lines, "Viva Questions", _resolve(data, "vivaQuestions"))
    _append_bullets(
        lines,
        "30 Second Revision",
        _resolve(data, "thirtySecondRevision"),
        limit=10,
    )

    return sanitize_note_text("\n".join(lines).strip())


def extract_exam_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Keep canonical exam-note fields for storage."""
    payload: dict[str, Any] = {}
    if data.get("topic"):
        payload["topic"] = data["topic"]
    if data.get("definition"):
        payload["definition"] = data["definition"]
    for canonical in (
        "whyItMatters",
        "keyConcepts",
        "detailedExplanation",
        "diagram",
        "table",
        "examples",
        "memoryTrick",
        "importantExamPoints",
        "commonMistakes",
        "frequentlyAskedQuestions",
        "vivaQuestions",
        "thirtySecondRevision",
    ):
        value = _resolve(data, canonical)
        if value is not None:
            payload[canonical] = value
    if data.get("summary") and "thirtySecondRevision" not in payload:
        payload["thirtySecondRevision"] = data["summary"]
    return payload


def is_exam_notes_result(data: dict[str, Any]) -> bool:
    if not data:
        return False
    markers = (
        "definition",
        "whyItMatters",
        "keyConcepts",
        "importantExamPoints",
        "thirtySecondRevision",
        "frequentlyAskedQuestions",
        "detailedExplanation",
        "keyPoints",
        "examQuestions",
    )
    return any(data.get(key) for key in markers)
