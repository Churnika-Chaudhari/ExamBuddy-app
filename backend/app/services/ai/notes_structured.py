"""Structured study-notes schema and markdown rendering for the mobile app."""

from __future__ import annotations

from typing import Any

from app.services.ai.notes_sanitizer import sanitize_note_text

STRUCTURED_NOTE_FIELDS = (
    "topic",
    "definition",
    "introduction",
    "whyUsed",
    "why_used",
    "workingPrinciple",
    "working_principle",
    "working",
    "architecture",
    "types",
    "detailedExplanation",
    "detailed_explanation",
    "conceptualExplanation",
    "conceptual_explanation",
    "stepByStepWorking",
    "step_by_step_working",
    "example",
    "realWorldExample",
    "real_world_example",
    "practicalExamples",
    "practical_examples",
    "diagram",
    "formula",
    "advantages",
    "disadvantages",
    "applications",
    "comparison",
    "commonMistakes",
    "common_mistakes",
    "frequentlyAskedQuestions",
    "interviewQuestions",
    "vivaQuestions",
    "keyPoints",
    "key_points",
    "examTips",
    "keywords",
    "summary",
    "components",
    "background",
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
        "whyUsed",
        "workingPrinciple",
        "working",
        "detailedExplanation",
        "conceptualExplanation",
        "conceptual_explanation",
        "stepByStepWorking",
        "advantages",
        "interviewQuestions",
        "frequentlyAskedQuestions",
        "keyPoints",
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
                name = _as_text(item.get("name") or item.get("title") or item.get("type") or item.get("point"))
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


def _append_diagram(lines: list[str], diagram: Any) -> None:
    text = _as_text(diagram)
    if not text:
        return
    lines.append("## Diagram")
    lines.append("```")
    lines.append(text)
    lines.append("```")
    lines.append("")


def _append_comparison(lines: list[str], comparison: Any) -> None:
    if not comparison:
        return
    if isinstance(comparison, str):
        text = comparison.strip()
        if text:
            lines.extend(["## Comparison Table", text, ""])
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
    title = f"Comparison Table: {left} vs {right}" if left and right else "Comparison Table"
    lines.append(f"## {title}")

    table = comparison.get("table") or comparison.get("rows") or []
    if isinstance(table, list) and table and all(isinstance(row, dict) for row in table):
        headers = ["Aspect", left or "Concept A", right or "Concept B"]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| --- | --- | --- |")
        for row in table:
            aspect = _as_text(row.get("aspect") or row.get("feature") or row.get("point"))
            left_val = _as_text(
                row.get("leftValue") or row.get("left") or row.get("a") or row.get("first")
            )
            right_val = _as_text(
                row.get("rightValue") or row.get("right") or row.get("b") or row.get("second")
            )
            if aspect:
                lines.append(f"| {aspect} | {left_val} | {right_val} |")
    elif isinstance(table, list):
        for row in table:
            if isinstance(row, str) and row.strip():
                lines.append(f"- {row.strip()}")
            elif isinstance(row, list):
                cells = [_as_text(c) for c in row]
                lines.append("- " + " — ".join(c for c in cells if c))
    else:
        summary = _as_text(comparison.get("summary") or comparison.get("description"))
        if summary:
            lines.append(summary)

    lines.append("")


def structured_notes_to_markdown(data: dict[str, Any]) -> str:
    """Render exam-ready structured JSON into the required Markdown outline."""
    topic = _as_text(data.get("topic") or data.get("title") or "Study Topic")
    lines: list[str] = [f"# {topic}", ""]

    _append_section(lines, "Definition", data.get("definition"))
    _append_section(lines, "Introduction", data.get("introduction") or data.get("background"))
    _append_section(lines, "Why it is used", data.get("whyUsed") or data.get("why_used"))
    _append_section(
        lines,
        "Working Principle",
        data.get("workingPrinciple") or data.get("working_principle") or data.get("working"),
    )
    _append_section(
        lines,
        "Architecture / Components",
        data.get("architecture") or data.get("components"),
    )
    _append_bullet_section(lines, "Types", data.get("types"))

    detailed = _as_text(
        data.get("detailedExplanation")
        or data.get("detailed_explanation")
        or data.get("conceptualExplanation")
        or data.get("conceptual_explanation")
    )
    _append_section(lines, "Detailed Explanation", detailed)

    _append_section(
        lines,
        "Step-by-step Working",
        data.get("stepByStepWorking") or data.get("step_by_step_working"),
    )
    _append_section(lines, "Example", data.get("example") or data.get("practicalExamples"))
    _append_section(
        lines,
        "Real-world Example",
        data.get("realWorldExample") or data.get("real_world_example"),
    )
    _append_diagram(lines, data.get("diagram"))
    _append_section(lines, "Formula", data.get("formula"))
    _append_bullet_section(lines, "Advantages", data.get("advantages"))
    _append_bullet_section(lines, "Disadvantages", data.get("disadvantages"))
    _append_bullet_section(lines, "Applications", data.get("applications"))
    _append_comparison(lines, data.get("comparison"))
    _append_bullet_section(
        lines,
        "Common Mistakes",
        data.get("commonMistakes") or data.get("common_mistakes"),
    )
    _append_qa_section(
        lines,
        "Frequently Asked Exam Questions",
        data.get("frequentlyAskedQuestions") or data.get("vivaQuestions"),
    )
    _append_qa_section(
        lines,
        "Interview Questions",
        data.get("interviewQuestions") or data.get("interview_questions"),
    )
    _append_bullet_section(
        lines,
        "Key Points to Remember",
        data.get("keyPoints") or data.get("key_points") or data.get("examTips"),
    )
    _append_bullet_section(lines, "Keywords", data.get("keywords"))
    _append_section(lines, "Summary", data.get("summary"))

    markdown = sanitize_note_text("\n".join(lines).strip())
    return markdown


def extract_structured_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Keep only structured note fields for storage/API metadata."""
    payload = {key: data[key] for key in STRUCTURED_NOTE_FIELDS if data.get(key) is not None}
    return payload
