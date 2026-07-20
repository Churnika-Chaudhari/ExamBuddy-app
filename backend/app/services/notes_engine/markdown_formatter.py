"""Markdown formatter for Professor Alex lecture notes (v18)."""

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
        for key in ("text", "description", "content", "value", "simpleExplanation"):
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
        # examQuestions may be { longAnswer: [], shortAnswer: [] }
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


def _append_exam_questions(lines: list[str], value: Any) -> None:
    if not value:
        return
    if isinstance(value, dict) and (
        value.get("longAnswer")
        or value.get("shortAnswer")
        or value.get("long_answer")
        or value.get("short_answer")
    ):
        lines.append("## University Exam Questions")
        long_q = value.get("longAnswer") or value.get("long_answer")
        short_q = value.get("shortAnswer") or value.get("short_answer")
        if long_q:
            lines.append("### Long Answer")
            for idx, (q, a) in enumerate(_qa_pairs(long_q), start=1):
                lines.append(f"#### LA{idx}. {q}")
                if a:
                    lines.append(f"**Answer:** {a}")
                lines.append("")
        if short_q:
            lines.append("### Short Answer")
            for idx, (q, a) in enumerate(_qa_pairs(short_q), start=1):
                lines.append(f"#### SA{idx}. {q}")
                if a:
                    lines.append(f"**Answer:** {a}")
                lines.append("")
        return
    _append_qa(lines, "University Exam Questions", value)


def _append_mcqs(lines: list[str], value: Any) -> None:
    if not isinstance(value, list) or not value:
        return
    lines.append("## MCQs")
    for idx, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue
        q = _as_text(item.get("question"))
        if not q:
            continue
        lines.append(f"### MCQ{idx}. {q}")
        options = item.get("options") or []
        if isinstance(options, list):
            for opt_i, opt in enumerate(options):
                label = chr(65 + opt_i) if opt_i < 26 else str(opt_i + 1)
                lines.append(f"- **{label}.** {_as_text(opt)}")
        ans = _as_text(item.get("answer") or item.get("correct"))
        if ans:
            lines.append(f"**Answer:** {ans}")
        expl = _as_text(item.get("explanation"))
        if expl:
            lines.append(f"**Why:** {expl}")
        lines.append("")


def _append_components(lines: list[str], value: Any, *, title: str = "Architecture / Components") -> None:
    if not value:
        return
    if isinstance(value, list) and value and isinstance(value[0], dict) and (
        value[0].get("purpose") or value[0].get("responsibility") or value[0].get("name")
    ):
        lines.append(f"## {title}")
        for item in value:
            if not isinstance(item, dict):
                continue
            name = _as_text(item.get("name") or item.get("title") or "Component")
            lines.append(f"### {name}")
            purpose = _as_text(item.get("purpose"))
            responsibility = _as_text(item.get("responsibility"))
            interaction = _as_text(item.get("interaction"))
            simple = _as_text(item.get("simpleExplanation") or item.get("description"))
            if purpose:
                lines.append(f"- **Purpose:** {purpose}")
            if responsibility:
                lines.append(f"- **Responsibility:** {responsibility}")
            if interaction:
                lines.append(f"- **Interaction:** {interaction}")
            if simple:
                lines.append(f"- **Simple explanation:** {simple}")
            lines.append("")
        return
    _append_bullets(lines, title, value)


def _append_table(lines: list[str], table: Any) -> None:
    if not table:
        return

    if isinstance(table, dict) and (table.get("compareWith") or table.get("left")):
        left = _as_text(table.get("left") or "A")
        right = _as_text(table.get("compareWith") or table.get("right") or "B")
        rows = table.get("table") or table.get("rows") or []
        lines.append(f"## Comparison: {left} vs {right}")
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
            lines.extend(["## Comparison", text, ""])
        return

    if not isinstance(table, dict):
        return

    title = _as_text(table.get("title") or "Comparison")
    headers = table.get("headers") or ["Aspect", "A", "B"]
    rows = table.get("rows") or []
    if not isinstance(headers, list) or not headers:
        return
    header_cells = [_as_text(h) for h in headers]
    lines.append(f"## Comparison: {title}" if title != "Comparison" else "## Comparison")
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
    """Render Professor Alex lecture JSON into markdown."""
    topic = _as_text(data.get("topic") or data.get("title") or "Study Topic")
    lines: list[str] = [f"# {topic}", ""]

    _append_section(lines, "1. What is it?", _resolve(data, "whatIsIt"))
    _append_section(lines, "2. Why do we need it?", _resolve(data, "whyNeeded"))
    _append_section(lines, "3. Real Life Analogy", _resolve(data, "realLifeAnalogy"))
    _append_section(lines, "4. Core Concept", _resolve(data, "coreConcept"))
    _append_section(lines, "5. How It Works", _resolve(data, "howItWorks"))

    architecture = _as_text(_resolve(data, "architecture"))
    components = _resolve(data, "components")
    if architecture:
        lines.append("## 6. Architecture / Components")
        lines.append(architecture)
        lines.append("")
        if isinstance(components, list) and components and isinstance(components[0], dict):
            for item in components:
                if not isinstance(item, dict):
                    continue
                name = _as_text(item.get("name") or item.get("title") or "Component")
                lines.append(f"### {name}")
                purpose = _as_text(item.get("purpose"))
                responsibility = _as_text(item.get("responsibility"))
                interaction = _as_text(item.get("interaction"))
                simple = _as_text(item.get("simpleExplanation") or item.get("description"))
                if purpose:
                    lines.append(f"- **Purpose:** {purpose}")
                if responsibility:
                    lines.append(f"- **Responsibility:** {responsibility}")
                if interaction:
                    lines.append(f"- **Interaction:** {interaction}")
                if simple:
                    lines.append(f"- **Simple explanation:** {simple}")
                lines.append("")
        elif components:
            for bullet in _as_bullets(components):
                lines.append(f"- {bullet}")
            lines.append("")
    else:
        _append_components(lines, components, title="6. Architecture / Components")

    _append_section(lines, "7. Visual Diagram", data.get("diagram"))
    _append_section(lines, "8. Real World Example", _resolve(data, "realWorldExample"))
    _append_section(lines, "9. Deep Dive", _resolve(data, "deepDive"))
    _append_bullets(lines, "10. Advantages", _resolve(data, "advantages"))
    _append_bullets(lines, "11. Disadvantages", _resolve(data, "disadvantages"))

    comparison = _resolve(data, "comparison")
    if comparison:
        # Ensure heading numbering in table helper by post-fixing title if needed
        start = len(lines)
        _append_table(lines, comparison)
        for i in range(start, len(lines)):
            if lines[i].startswith("## Comparison"):
                lines[i] = lines[i].replace("## Comparison", "## 12. Comparison", 1)
                break

    _append_bullets(lines, "13. Common Mistakes", _resolve(data, "commonMistakes"))
    _append_qa(lines, "14. Interview / Viva Questions", _resolve(data, "vivaQuestions"))
    _append_exam_questions(lines, _resolve(data, "examQuestions"))
    # Fix exam questions heading number if helper used generic title
    for i, line in enumerate(lines):
        if line == "## University Exam Questions":
            lines[i] = "## 15. University Exam Questions"
            break
    _append_mcqs(lines, _resolve(data, "mcqs"))
    for i, line in enumerate(lines):
        if line == "## MCQs":
            lines[i] = "## 15. University Exam Questions — MCQs"
            break
    _append_bullets(lines, "16. Memory Tricks", _resolve(data, "memoryTricks"))
    _append_bullets(lines, "17. Revision Sheet", _resolve(data, "revisionSheet"), limit=15)
    _append_bullets(lines, "18. Key Takeaways", _resolve(data, "keyTakeaways"))

    return sanitize_note_text("\n".join(lines).strip())


def extract_exam_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Keep canonical lecture-note fields for storage."""
    payload: dict[str, Any] = {}
    if data.get("topic"):
        payload["topic"] = data["topic"]
    for canonical in (
        "whatIsIt",
        "whyNeeded",
        "realLifeAnalogy",
        "coreConcept",
        "howItWorks",
        "architecture",
        "components",
        "diagram",
        "realWorldExample",
        "deepDive",
        "advantages",
        "disadvantages",
        "comparison",
        "commonMistakes",
        "vivaQuestions",
        "examQuestions",
        "mcqs",
        "memoryTricks",
        "revisionSheet",
        "keyTakeaways",
    ):
        value = _resolve(data, canonical)
        if value is not None:
            payload[canonical] = value
    # Preserve plain definition alias for older clients reading structured_notes
    if payload.get("whatIsIt") and not data.get("definition"):
        payload["definition"] = payload["whatIsIt"]
    return payload


def is_exam_notes_result(data: dict[str, Any]) -> bool:
    if not data:
        return False
    markers = (
        "whatIsIt",
        "whyNeeded",
        "realLifeAnalogy",
        "coreConcept",
        "howItWorks",
        "keyTakeaways",
        "revisionSheet",
        "definition",
        "whyItMatters",
        "importantExamPoints",
        "thirtySecondRevision",
        "detailedExplanation",
        "examQuestions",
    )
    return any(data.get(key) for key in markers)
