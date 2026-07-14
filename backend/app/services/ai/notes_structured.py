"""Structured study-notes schema and markdown rendering for the mobile app."""

from __future__ import annotations

from app.services.ai.notes_sanitizer import sanitize_note_text, sanitize_rag_passage

STRUCTURED_NOTE_FIELDS = (
    "topic",
    "definition",
    "conceptualExplanation",
    "conceptual_explanation",
    "practicalExamples",
    "practical_examples",
    "introduction",
    "background",
    "working",
    "architecture",
    "diagram",
    "components",
    "types",
    "features",
    "advantages",
    "disadvantages",
    "applications",
    "example",
    "comparison",
    "interviewQuestions",
    "vivaQuestions",
    "universityQuestions",
    "examTips",
    "keywords",
    "summary",
)


def is_structured_notes_result(data: dict[str, Any]) -> bool:
    """True when the AI returned section fields instead of a plain notes string."""
    if not data:
        return False
    if data.get("notes") and not any(data.get(f) for f in STRUCTURED_NOTE_FIELDS if f != "topic"):
        return False
    markers = (
        "definition",
        "introduction",
        "conceptualExplanation",
        "conceptual_explanation",
        "working",
        "components",
        "advantages",
        "practicalExamples",
        "interviewQuestions",
        "vivaQuestions",
    )
    return any(data.get(key) for key in markers)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return sanitize_note_text(value.strip())
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        for key in ("text", "description", "content", "value"):
            if value.get(key):
                return str(value[key]).strip()
        return ""
    if isinstance(value, list):
        parts = [_as_text(item) for item in value]
        return "\n".join(p for p in parts if p)
    return str(value).strip()


def _as_bullets(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if len(lines) == 1:
            return [lines[0]]
        return [ln.lstrip("-•* ").strip() for ln in lines if ln.strip()]
    if isinstance(value, list):
        bullets: list[str] = []
        for item in value:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    bullets.append(text)
            elif isinstance(item, dict):
                name = _as_text(item.get("name") or item.get("title") or item.get("type"))
                desc = _as_text(
                    item.get("description")
                    or item.get("detail")
                    or item.get("explanation")
                    or item.get("text")
                )
                if name and desc:
                    bullets.append(f"**{name}** — {desc}")
                elif name:
                    bullets.append(name)
                elif desc:
                    bullets.append(desc)
        return bullets
    return [_as_text(value)] if _as_text(value) else []


def _qa_bullets(value: Any) -> list[tuple[str, str]]:
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


def _append_bullet_section(lines: list[str], title: str, content: Any) -> None:
    bullets = _as_bullets(content)
    if not bullets:
        return
    lines.append(f"## {title}")
    lines.extend(f"- {bullet}" for bullet in bullets)
    lines.append("")


def _append_qa_section(lines: list[str], title: str, content: Any) -> None:
    pairs = _qa_bullets(content)
    if not pairs:
        return
    lines.append(f"## {title}")
    for idx, (question, answer) in enumerate(pairs, start=1):
        lines.append(f"### Q{idx}. {question}")
        if answer:
            lines.append(f"**Answer:** {answer}")
        lines.append("")


def _append_comparison(lines: list[str], comparison: Any) -> None:
    if not comparison:
        return
    if isinstance(comparison, str):
        text = comparison.strip()
        if text:
            lines.extend([f"## Comparison", text, ""])
        return
    if not isinstance(comparison, dict):
        return

    left = _as_text(comparison.get("left") or comparison.get("topicA") or comparison.get("a"))
    right = _as_text(
        comparison.get("right")
        or comparison.get("compareWith")
        or comparison.get("topicB")
        or comparison.get("b")
    )
    title = f"Comparison: {left} vs {right}" if left and right else "Comparison"
    lines.append(f"## {title}")

    table = comparison.get("table") or comparison.get("rows") or []
    if isinstance(table, list) and table:
        for row in table:
            if isinstance(row, dict):
                aspect = _as_text(row.get("aspect") or row.get("feature") or row.get("point"))
                left_val = _as_text(
                    row.get("leftValue")
                    or row.get("left")
                    or row.get("a")
                    or row.get("first")
                )
                right_val = _as_text(
                    row.get("rightValue")
                    or row.get("right")
                    or row.get("b")
                    or row.get("second")
                )
                if aspect and left_val and right_val:
                    lines.append(f"- **{aspect}**: {left} — {left_val}; {right} — {right_val}")
                elif aspect:
                    lines.append(f"- **{aspect}**: {left_val or right_val}")
                else:
                    line = _as_text(row)
                    if line:
                        lines.append(f"- {line}")
            elif isinstance(row, str) and row.strip():
                lines.append(f"- {row.strip()}")
    else:
        summary = _as_text(comparison.get("summary") or comparison.get("description"))
        if summary:
            lines.append(summary)

    lines.append("")


def _build_conceptual_explanation(data: dict[str, Any]) -> str:
    direct = _as_text(
        data.get("conceptualExplanation")
        or data.get("conceptual_explanation")
        or data.get("concept")
    )
    if direct:
        return direct

    parts: list[str] = []
    for key in (
        "introduction",
        "background",
        "working",
        "process",
        "architecture",
        "architectureFlow",
        "diagram",
    ):
        text = _as_text(data.get(key))
        if text:
            parts.append(text)

    for key in ("components", "types", "features"):
        bullets = _as_bullets(data.get(key))
        if bullets:
            parts.append("\n".join(f"- {b}" for b in bullets))

    return "\n\n".join(parts).strip()


def _build_practical_examples(data: dict[str, Any]) -> str:
    direct = _as_text(
        data.get("practicalExamples")
        or data.get("practical_examples")
        or data.get("examples")
    )
    if direct:
        return direct

    parts: list[str] = []
    example = _as_text(data.get("example"))
    if example:
        parts.append(example)
    apps = _as_bullets(data.get("applications"))
    if apps:
        parts.extend(f"- {a}" for a in apps)
    return "\n\n".join(parts).strip()


def structured_notes_to_markdown(data: dict[str, Any]) -> str:
    """Render clean exam-oriented structured JSON into markdown."""
    topic = _as_text(data.get("topic") or data.get("title") or "Study Topic")
    lines: list[str] = [f"# {topic}"]

    priority = _as_text(data.get("exam_priority") or data.get("examPriority"))
    if priority and "frequently" in priority.lower():
        lines.extend(["⭐ Frequently Asked in Exams", ""])

    _append_section(lines, "Definition", data.get("definition"))

    conceptual = _build_conceptual_explanation(data)
    _append_section(lines, "Conceptual Explanation", conceptual)

    practical = _build_practical_examples(data)
    _append_section(lines, "Practical Examples", practical)

    _append_bullet_section(lines, "Advantages", data.get("advantages"))
    _append_bullet_section(lines, "Disadvantages", data.get("disadvantages"))
    _append_comparison(lines, data.get("comparison"))
    _append_qa_section(
        lines,
        "Interview Questions",
        data.get("interviewQuestions") or data.get("interview_questions"),
    )
    _append_qa_section(
        lines,
        "Viva Questions",
        data.get("vivaQuestions") or data.get("viva_questions"),
    )
    _append_bullet_section(lines, "Exam Tips", data.get("examTips") or data.get("exam_tips"))
    _append_bullet_section(lines, "Keywords", data.get("keywords"))
    _append_section(lines, "Summary", data.get("summary"))

    markdown = sanitize_note_text("\n".join(lines).strip())
    return markdown


def extract_structured_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Keep only structured note fields for storage/API metadata."""
    payload = {key: data[key] for key in STRUCTURED_NOTE_FIELDS if data.get(key) is not None}
    if data.get("exam_priority"):
        payload["exam_priority"] = data["exam_priority"]
    return payload
