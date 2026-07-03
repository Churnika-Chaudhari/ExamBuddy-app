"""
Expert Academic Question Paper Analyzer.
Output: syllabus topics with units, priority tiers, and predictions.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from typing import Any

from app.services.pipeline.text_preprocessor import preprocess_pyq_text
from app.utils.syllabus_concept_extractor import extract_concepts_from_questions
from app.utils.topic_extractor import is_valid_topic
from app.services.pipeline.topic_pipeline import extract_and_merge_topics, merge_similar_topics

_QUESTION_PREFIX = re.compile(
    r"^(?:\d+[\).\]]|\([a-z]\)|[Qq]\d+[\).:]|[ivxIVX]+[\).\]])\s*",
    re.I,
)
_MARKS_SUFFIX = re.compile(r"\[?\s*\d+\s*(?:marks?|m)\s*\]?\s*$", re.I)

from app.utils.syllabus_units import assign_syllabus_unit


def _extract_question_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if len(line) < 10:
            continue
        line = _QUESTION_PREFIX.sub("", line).strip()
        line = _MARKS_SUFFIX.sub("", line).strip()
        if re.match(r"^(\d+[\).\]]|[Qq]\d+)", line):
            lines.append(line)
        elif "?" in line or re.search(
            r"\b(explain|define|describe|write|discuss|what is|what are|list|state|mention|differentiate)\b",
            line,
            re.I,
        ):
            lines.append(line)
    if not lines:
        chunks = re.split(r"\n{2,}|---+", text)
        lines = [c.strip() for c in chunks if 15 <= len(c.strip()) <= 500]
    return lines[:800]


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _merge_similar_topics(counter: dict[str, int]) -> dict[str, int]:
    keys = list(counter.keys())
    absorb: dict[str, str] = {}
    for i, a in enumerate(keys):
        if a in absorb:
            continue
        for b in keys[i + 1 :]:
            if b in absorb:
                continue
            al, bl = a.lower(), b.lower()
            if al == bl or ((al in bl or bl in al) and _similarity(al, bl) >= 0.6):
                parent = a if counter[a] >= counter[b] else b
                child = b if parent == a else a
                absorb[child] = parent

    merged: dict[str, int] = defaultdict(int)
    for topic, count in counter.items():
        root = topic
        while root in absorb:
            root = absorb[root]
        if is_valid_topic(root):
            merged[root] += count
    return dict(merged)


def _build_row(topic: str, frequency: int) -> dict[str, Any]:
    return {
        "topic": topic,
        "unit": assign_syllabus_unit(topic),
        "frequency": frequency,
    }


def build_consolidated_analysis(
    content: str,
    *,
    subject: str | None = None,
    num_documents: int = 1,
) -> dict[str, Any]:
    preprocessed = preprocess_pyq_text(content)
    pipeline_result = extract_and_merge_topics(
        preprocessed.question_lines,
        num_documents=num_documents,
    )
    if pipeline_result:
        return pipeline_result

    lines = preprocessed.question_lines or _extract_question_lines(preprocessed.cleaned_text)
    raw_counter = extract_concepts_from_questions(lines)

    if not raw_counter:
        return _empty_result(num_documents, len(lines))

    merged = merge_similar_topics(dict(raw_counter))
    ranked = sorted(merged.items(), key=lambda x: -x[1])
    if not ranked:
        return _empty_result(num_documents, len(lines))

    topic_frequency_table = [_build_row(topic, freq) for topic, freq in ranked]

    high_priority = [r for r in topic_frequency_table if r["frequency"] >= 3]
    medium_priority = [r for r in topic_frequency_table if r["frequency"] == 2]
    low_priority = [r for r in topic_frequency_table if r["frequency"] == 1]

    # Predicted important: high + medium, sorted by frequency
    predicted = sorted(
        high_priority + medium_priority,
        key=lambda x: -x["frequency"],
    )

    topic_groups: dict[str, list[str]] = defaultdict(list)
    for row in topic_frequency_table:
        topic_groups[row["unit"]].append(row["topic"])

    groups_list = [
        {"group": unit, "topics": topics}
        for unit, topics in sorted(topic_groups.items(), key=lambda x: -len(x[1]))
    ]

    # API compat fields
    topic_table_compat = [
        {
            "topic": r["topic"],
            "frequency": r["frequency"],
            "importance": (
                "High" if r["frequency"] >= 3
                else "Medium" if r["frequency"] == 2
                else "Low"
            ),
        }
        for r in topic_frequency_table
    ]

    academic_table = [{"topic": r["topic"], "frequency": r["frequency"]} for r in topic_frequency_table]

    return {
        "repeated_questions": [],
        "topic_frequency": {r["topic"]: r["frequency"] for r in topic_frequency_table},
        "important_topics": [
            {
                "topic": r["topic"],
                "score": round(r["frequency"] / ranked[0][1], 2),
                "reason": f"{r['unit']} — asked {r['frequency']} time(s)",
            }
            for r in predicted[:15]
        ],
        "topic_frequency_table": topic_frequency_table,
        "topic_table": topic_table_compat,
        "academic_topic_table": academic_table,
        "high_priority_topics": high_priority,
        "medium_priority_topics": medium_priority,
        "low_priority_topics": low_priority,
        "predicted_important_topics": predicted,
        "most_important_topics": high_priority,
        "frequently_asked_topics": high_priority + medium_priority,
        "rarely_asked_topics": low_priority,
        "topic_groups": groups_list,
        "syllabus_topics": [r["topic"] for r in topic_frequency_table],
        "exam_patterns": [],
        "summary": (
            f"Analyzed {num_documents} paper(s): {len(topic_frequency_table)} syllabus topics "
            f"from {len(lines)} questions. "
            f"High priority: {len(high_priority)}, Medium: {len(medium_priority)}, "
            f"Low: {len(low_priority)}."
        ),
    }


def _empty_result(num_documents: int, num_lines: int) -> dict[str, Any]:
    return {
        "repeated_questions": [],
        "topic_frequency": {},
        "important_topics": [],
        "topic_frequency_table": [],
        "topic_table": [],
        "academic_topic_table": [],
        "high_priority_topics": [],
        "medium_priority_topics": [],
        "low_priority_topics": [],
        "predicted_important_topics": [],
        "most_important_topics": [],
        "frequently_asked_topics": [],
        "rarely_asked_topics": [],
        "topic_groups": [],
        "syllabus_topics": [],
        "exam_patterns": [],
        "summary": f"No syllabus topics found in {num_documents} paper(s).",
    }
