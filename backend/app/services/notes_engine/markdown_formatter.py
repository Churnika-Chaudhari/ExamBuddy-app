"""Markdown formatter for ExamBuddy exam notes (v19)."""

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
        for key in ("text", "description", "content", "value", "answer"):
            if value.get(key):
                return str(value[key]).strip()
    return str(value).strip()


def _as_bullets(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [ln.strip().lstrip("-•* ").strip() for ln in value.splitlines() if ln.strip()]
    if isinstance(value, list):
        bullets: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                bullets.append(item.strip())
            elif isinstance(item, dict):
                name = _as_text(
                    item.get("name") or item.get("title") or item.get("concept") or item.get("mistake")
                )
                desc = _as_text(
                    item.get("description")
                    or item.get("detail")
                    or item.get("explanation")
                    or item.get("text")
                    or item.get("why")
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
    if isinstance(value, dict):
        for key in ("longAnswer", "shortAnswer", "long_answer", "short_answer", "items"):
            if key in value:
                pairs.extend(_qa_pairs(value.get(key)))
        if pairs:
            return pairs
        q = _as_text(value.get("question") or value.get("q"))
        a = _as_text(value.get("answer") or value.get("a"))
        if q:
            return [(q, a)]
        return []
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


def _append_diagram(lines: list[str], value: Any) -> None:
    text = _as_text(value)
    if not text:
        return
    lines.append("## Diagram")
    # Mermaid: wrap if not already fenced
    stripped = text.strip()
    if stripped.startswith("```"):
        lines.extend([stripped, ""])
        return
    lower = stripped.lower()
    if lower.startswith(("flowchart", "sequenceDiagram", "graph ", "classDiagram", "erDiagram", "stateDiagram")):
        lines.extend(["```mermaid", stripped, "```", ""])
        return
    lines.extend(["```", stripped, "```", ""])


def _append_table(lines: list[str], table: Any) -> None:
    if not table:
        return
    if isinstance(table, str):
        text = table.strip()
        if text:
            lines.extend(["## Comparison", text, ""])
        return
    if not isinstance(table, dict):
        return

    title = _as_text(table.get("title") or "Comparison")
    headers = table.get("headers") or ["Aspect", "A", "B"]
    rows = table.get("rows") or table.get("table") or []
    if isinstance(headers, list) and headers:
        header_cells = [_as_text(h) for h in headers]
        lines.append(f"## Comparison: {title}" if title else "## Comparison")
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
    """Render ExamBuddy exam-note JSON into markdown."""
    topic = _as_text(data.get("topic") or data.get("title") or "Study Topic")
    lines: list[str] = [f"# {topic}", ""]

    topic_type = _as_text(_resolve(data, "topicType"))
    if topic_type:
        lines.extend([f"**Type:** {topic_type}", ""])

    _append_section(lines, "Definition", _resolve(data, "definition"))
    _append_section(lines, "Introduction", _resolve(data, "introduction"))
    _append_section(lines, "Detailed Explanation", _resolve(data, "detailedExplanation"))
    _append_bullets(lines, "Key Concepts", _resolve(data, "keyConcepts"))
    _append_bullets(lines, "Characteristics", _resolve(data, "characteristics"))
    _append_section(lines, "Architecture", _resolve(data, "architecture"))
    _append_section(lines, "Working", _resolve(data, "working"))
    _append_section(lines, "Syntax", _resolve(data, "syntax"))
    _append_section(lines, "Pseudocode", _resolve(data, "pseudocode"))
    _append_section(lines, "Code Example", _resolve(data, "codeExample"))
    _append_section(lines, "Output", _resolve(data, "output"))
    _append_diagram(lines, _resolve(data, "diagram"))
    _append_section(lines, "Example", _resolve(data, "example"))
    _append_section(lines, "Time Complexity", _resolve(data, "timeComplexity"))
    _append_section(lines, "Space Complexity", _resolve(data, "spaceComplexity"))
    _append_bullets(lines, "Advantages", _resolve(data, "advantages"))
    _append_bullets(lines, "Disadvantages", _resolve(data, "disadvantages"))
    _append_bullets(lines, "Applications", _resolve(data, "applications"))
    _append_bullets(lines, "Important Formulae", _resolve(data, "formulae"))
    _append_table(lines, _resolve(data, "comparison"))
    _append_qa(lines, "Frequently Asked University Questions", _resolve(data, "frequentlyAskedQuestions"))
    _append_section(lines, "2-Mark Answer", _resolve(data, "twoMarkAnswer"))
    _append_section(lines, "5-Mark Answer", _resolve(data, "fiveMarkAnswer"))
    _append_section(lines, "10-Mark Answer", _resolve(data, "tenMarkAnswer"))
    _append_qa(lines, "Viva Questions", _resolve(data, "vivaQuestions"))
    _append_qa(lines, "Interview Questions", _resolve(data, "interviewQuestions"))
    _append_bullets(lines, "Common Mistakes", _resolve(data, "commonMistakes"))
    _append_bullets(lines, "Revision Summary", _resolve(data, "revisionSummary"), limit=12)
    _append_bullets(lines, "Keywords", _resolve(data, "keywords"))

    return sanitize_note_text("\n".join(lines).strip())


def extract_exam_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Keep canonical exam-note fields for storage."""
    payload: dict[str, Any] = {}
    if data.get("topic"):
        payload["topic"] = data["topic"]
    for canonical in (
        "topicType",
        "definition",
        "introduction",
        "detailedExplanation",
        "keyConcepts",
        "working",
        "diagram",
        "example",
        "advantages",
        "disadvantages",
        "applications",
        "formulae",
        "frequentlyAskedQuestions",
        "twoMarkAnswer",
        "fiveMarkAnswer",
        "tenMarkAnswer",
        "vivaQuestions",
        "interviewQuestions",
        "commonMistakes",
        "revisionSummary",
        "keywords",
        "characteristics",
        "architecture",
        "syntax",
        "codeExample",
        "output",
        "pseudocode",
        "timeComplexity",
        "spaceComplexity",
        "comparison",
    ):
        value = _resolve(data, canonical)
        if value is not None:
            payload[canonical] = value
    return payload


def is_exam_notes_result(data: dict[str, Any]) -> bool:
    if not data:
        return False
    markers = (
        "definition",
        "whatIsIt",
        "introduction",
        "detailedExplanation",
        "deepDive",
        "keyConcepts",
        "working",
        "howItWorks",
        "twoMarkAnswer",
        "fiveMarkAnswer",
        "tenMarkAnswer",
        "revisionSummary",
        "revisionSheet",
        "frequentlyAskedQuestions",
        "vivaQuestions",
        "importantExamPoints",
        "thirtySecondRevision",
    )
    return any(data.get(key) for key in markers)
