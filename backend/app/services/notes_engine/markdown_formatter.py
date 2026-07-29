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
    """Render ExamBuddy exam-note JSON into markdown (skip empty sections)."""
    topic = _as_text(data.get("topic") or data.get("title") or "Study Topic")
    lines: list[str] = [f"# {topic}", ""]

    topic_type = _as_text(_resolve(data, "topicType"))
    if topic_type:
        lines.extend([f"**Type:** {topic_type}", ""])

    _append_section(lines, "Definition", _resolve(data, "definition"))
    _append_section(lines, "Introduction", _resolve(data, "introduction"))
    _append_section(lines, "Working", _resolve(data, "working"))
    _append_section(lines, "Architecture", _resolve(data, "architecture"))
    _append_section(lines, "Algorithm", _resolve(data, "algorithm"))
    _append_section(lines, "Formula", _resolve(data, "formula") or _resolve(data, "formulae"))
    _append_diagram(lines, _resolve(data, "diagram"))
    # Flowchart uses same Mermaid/ASCII rendering helper
    flowchart = _resolve(data, "flowchart")
    if _as_text(flowchart):
        before = len(lines)
        _append_diagram(lines, flowchart)
        # Retitle Diagram → Flowchart when this block was appended
        for i in range(before, len(lines)):
            if lines[i] == "## Diagram":
                lines[i] = "## Flowchart"
                break
    _append_section(lines, "Pseudocode", _resolve(data, "pseudocode"))
    _append_section(lines, "Syntax", _resolve(data, "syntax"))
    _append_section(lines, "Code Example", _resolve(data, "codeExample"))
    _append_section(lines, "SQL Example", _resolve(data, "sqlExample"))
    _append_section(lines, "Output", _resolve(data, "output"))
    _append_section(lines, "Example", _resolve(data, "example"))
    _append_section(lines, "Time Complexity", _resolve(data, "timeComplexity"))
    _append_section(lines, "Space Complexity", _resolve(data, "spaceComplexity"))
    _append_bullets(lines, "Advantages", _resolve(data, "advantages"))
    _append_bullets(lines, "Disadvantages", _resolve(data, "disadvantages"))
    _append_bullets(lines, "Applications", _resolve(data, "applications"))
    _append_table(lines, _resolve(data, "comparison"))
    # Ensure comparison heading matches requested name when present
    for i, line in enumerate(lines):
        if line.startswith("## Comparison"):
            lines[i] = "## Comparison Table" if line == "## Comparison" else line.replace(
                "## Comparison:", "## Comparison Table:", 1
            )
            break
    _append_qa(lines, "Frequently Asked Questions", _resolve(data, "frequentlyAskedQuestions"))
    _append_section(lines, "2-Mark Answer", _resolve(data, "twoMarkAnswer"))
    _append_section(lines, "5-Mark Answer", _resolve(data, "fiveMarkAnswer"))
    _append_section(lines, "10-Mark Answer", _resolve(data, "tenMarkAnswer"))
    _append_bullets(lines, "Revision Summary", _resolve(data, "revisionSummary"), limit=12)

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
        "working",
        "architecture",
        "algorithm",
        "formula",
        "diagram",
        "flowchart",
        "pseudocode",
        "syntax",
        "codeExample",
        "sqlExample",
        "example",
        "timeComplexity",
        "spaceComplexity",
        "advantages",
        "disadvantages",
        "applications",
        "comparison",
        "frequentlyAskedQuestions",
        "twoMarkAnswer",
        "fiveMarkAnswer",
        "tenMarkAnswer",
        "revisionSummary",
        "output",
    ):
        value = _resolve(data, canonical)
        if value is not None:
            payload[canonical] = value
    return payload


# =============================================================================
# v30 — Sectioned NotebookLM-style markdown renderer.
#
# Renders the merged structured dict (11 batches — see schema.SECTION_ORDER)
# into ONE long-form textbook-chapter markdown document covering every
# required heading. A heading with no accurate content for the topic renders
# "Not Applicable" — it is never omitted.
# =============================================================================


def _na(value: Any) -> str:
    text = _as_text(value)
    return text if text else "Not Applicable"


def _append_section_h1(lines: list[str], title: str, value: Any) -> None:
    lines.append(f"# {title}")
    lines.append("")
    lines.append(_na(value))
    lines.append("")


def _append_code_section_h1(lines: list[str], title: str, value: Any) -> None:
    lines.append(f"# {title}")
    lines.append("")
    text = _as_text(value)
    if not text or text.strip().lower() == "not applicable":
        lines.append("Not Applicable")
        lines.append("")
        return
    stripped = text.strip()
    if stripped.startswith("```"):
        lines.extend([stripped, ""])
    else:
        lines.extend(["```", stripped, "```", ""])


def _append_diagram_h1(lines: list[str], title: str, value: Any) -> None:
    lines.append(f"# {title}")
    lines.append("")
    text = _as_text(value)
    if not text or text.strip().lower() == "not applicable":
        lines.append("Not Applicable")
        lines.append("")
        return
    stripped = text.strip()
    if stripped.startswith("```"):
        lines.extend([stripped, ""])
        return
    lower = stripped.lower()
    if lower.startswith(
        ("flowchart", "sequencediagram", "graph ", "graph td", "graph lr", "classdiagram", "erdiagram", "statediagram")
    ):
        lines.extend(["```mermaid", stripped, "```", ""])
    else:
        lines.extend(["```", stripped, "```", ""])


def _append_bullets_h1(lines: list[str], title: str, value: Any) -> None:
    lines.append(f"# {title}")
    lines.append("")
    bullets = _as_bullets(value)
    if not bullets:
        lines.append("Not Applicable")
    else:
        lines.extend(f"- {b}" for b in bullets)
    lines.append("")


def _table_rows(items: Any) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                point = _as_text(item.get("point") or item.get("title") or item.get("name"))
                explanation = _as_text(
                    item.get("explanation") or item.get("description") or item.get("detail")
                )
                if point or explanation:
                    rows.append((point or explanation, explanation if point else ""))
            elif isinstance(item, str) and item.strip():
                text = item.strip()
                if " — " in text:
                    point, explanation = text.split(" — ", 1)
                elif ": " in text:
                    point, explanation = text.split(": ", 1)
                else:
                    point, explanation = text, ""
                rows.append((point.strip(), explanation.strip()))
    elif isinstance(items, str) and items.strip():
        rows.append((items.strip(), ""))
    return rows


def _append_kv_table_h1(
    lines: list[str], title: str, items: Any, *, col1: str = "Point", col2: str = "Explanation"
) -> None:
    lines.append(f"# {title}")
    lines.append("")
    rows = _table_rows(items)
    if not rows:
        lines.append("Not Applicable")
        lines.append("")
        return
    lines.append(f"| {col1} | {col2} |")
    lines.append("|---|---|")
    for point, explanation in rows:
        point_cell = point.replace("|", "/").replace("\n", " ").strip()
        explanation_cell = explanation.replace("|", "/").replace("\n", " ").strip()
        lines.append(f"| {point_cell} | {explanation_cell} |")
    lines.append("")


def _append_comparison_tables_h1(lines: list[str], comparisons: Any) -> None:
    lines.append("# Comparison")
    lines.append("")
    tables: list[dict[str, Any]] = []
    if isinstance(comparisons, list):
        tables = [t for t in comparisons if isinstance(t, dict)]
    elif isinstance(comparisons, dict):
        tables = [comparisons]

    rendered_any = False
    for table in tables:
        headers = table.get("headers")
        rows = table.get("rows") or []
        if not isinstance(headers, list) or not headers:
            continue
        header_cells = [_as_text(h) or "—" for h in headers]
        title = _as_text(table.get("title"))
        lines.append(f"### {title}" if title else "### Comparison")
        lines.append("| " + " | ".join(header_cells) + " |")
        lines.append("|" + "|".join(["---"] * len(header_cells)) + "|")
        for row in rows:
            if isinstance(row, list):
                cells = [_as_text(c) for c in row[: len(header_cells)]]
                while len(cells) < len(header_cells):
                    cells.append("")
            elif isinstance(row, dict):
                cells = [_as_text(row.get(h, "")) for h in headers]
            else:
                continue
            lines.append("| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in cells) + " |")
        lines.append("")
        rendered_any = True

    if not rendered_any:
        lines.append("Not Applicable")
        lines.append("")


def _append_qa_h1(lines: list[str], title: str, value: Any) -> None:
    lines.append(f"# {title}")
    lines.append("")
    pairs = _qa_pairs(value)
    if not pairs:
        lines.append("Not Applicable")
        lines.append("")
        return
    for idx, (question, answer) in enumerate(pairs, start=1):
        lines.append(f"### Q{idx}. {question}")
        if answer:
            lines.append(f"**Answer:** {answer}")
        lines.append("")


def render_sectioned_markdown(data: dict[str, Any]) -> str:
    """Render the merged v30 sectioned-engine structured dict into ONE
    long-form textbook-chapter markdown document (~2500-5000 words) covering
    every required heading. Never omits a heading — "Not Applicable" instead."""
    topic = _as_text(data.get("topic")) or "Study Topic"
    subject = _as_text(data.get("subject"))
    exam_priority = _as_text(data.get("exam_priority"))

    lines: list[str] = [f"# {topic}", ""]
    meta_bits = [f"**Subject:** {subject}" if subject else "", f"**Exam Priority:** {exam_priority}" if exam_priority else ""]
    meta_bits = [b for b in meta_bits if b]
    if meta_bits:
        lines.append("  |  ".join(meta_bits))
        lines.append("")

    lines.append("# Definition")
    lines.append("")
    lines.append("### Simple")
    lines.append(_na(data.get("definition_simple")))
    lines.append("")
    lines.append("### Technical")
    lines.append(_na(data.get("definition_technical")))
    lines.append("")
    lines.append("### Exam-Ready")
    lines.append(_na(data.get("definition_exam")))
    lines.append("")

    _append_section_h1(lines, "Introduction", data.get("introduction"))
    _append_section_h1(lines, "Core Concept", data.get("core_concept"))
    _append_section_h1(lines, "Working Principle", data.get("working_principle"))
    _append_section_h1(lines, "Architecture / Components", data.get("architecture"))
    _append_diagram_h1(lines, "Flow Diagram", data.get("diagram"))
    _append_section_h1(lines, "Mathematical Formula", data.get("formula"))
    _append_code_section_h1(lines, "Algorithm", data.get("algorithm"))

    examples = _as_bullets(data.get("examples"))
    lines.append("# Example")
    lines.append("")
    if examples:
        for idx, example in enumerate(examples, start=1):
            lines.append(f"**Example {idx}.** {example}")
            lines.append("")
    else:
        lines.append("Not Applicable")
        lines.append("")

    _append_kv_table_h1(lines, "Advantages", data.get("advantages"))
    _append_kv_table_h1(lines, "Disadvantages", data.get("disadvantages"))
    _append_bullets_h1(lines, "Applications", data.get("applications"))
    _append_comparison_tables_h1(lines, data.get("comparison"))
    _append_section_h1(lines, "PYQ Perspective", data.get("pyq_perspective"))
    _append_section_h1(lines, "2 Marks Answer", data.get("exam_answer_2m"))
    _append_section_h1(lines, "5 Marks Answer", data.get("exam_answer_5m"))
    _append_section_h1(lines, "10 Marks Answer", data.get("exam_answer_10m"))
    _append_qa_h1(lines, "Viva Questions", data.get("viva"))
    _append_qa_h1(lines, "Interview Questions", data.get("interview"))
    _append_bullets_h1(lines, "Common Mistakes", data.get("common_mistakes"))
    _append_bullets_h1(lines, "Memory Tricks", data.get("memory_tricks"))
    _append_bullets_h1(lines, "Revision Notes", data.get("revision_points"))

    lines.append("# Keywords")
    lines.append("")
    keywords = _as_bullets(data.get("keywords"))
    lines.append(", ".join(keywords) if keywords else "Not Applicable")
    lines.append("")

    lines.append("# Summary")
    lines.append("")
    summary_text = _as_text(data.get("summary"))
    if summary_text:
        for line in summary_text.splitlines():
            if line.strip():
                lines.append(f"- {line.strip()}")
    else:
        lines.append("Not Applicable")
    lines.append("")

    return sanitize_note_text("\n".join(lines).strip())


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
