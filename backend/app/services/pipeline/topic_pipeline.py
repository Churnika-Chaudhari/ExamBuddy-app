"""
Academic topic extraction, canonical merging, and duplicate removal.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from app.utils.syllabus_concept_extractor import extract_concepts_from_questions
from app.utils.syllabus_units import assign_syllabus_unit
from app.utils.topic_extractor import _title_case_topic, is_valid_topic

# Variants like "Advantages of Virtual Memory" → canonical "Virtual Memory"
_TOPIC_VARIANT_PREFIX = re.compile(
    r"^(?:"
    r"advantages?(?:\s+and\s+disadvantages?)?\s+of|"
    r"disadvantages?\s+of|"
    r"need(?:s)?\s+of|"
    r"working\s+of|"
    r"workings?\s+of|"
    r"types?\s+of|"
    r"features?\s+of|"
    r"functions?\s+of|"
    r"applications?\s+of|"
    r"importance\s+of|"
    r"introduction\s+to|"
    r"overview\s+of|"
    r"basics?\s+of|"
    r"concept\s+of|"
    r"principles?\s+of|"
    r"architecture\s+of|"
    r"implementation\s+of|"
    r"detection\s+of|"
    r"prevention\s+of|"
    r"recovery\s+(?:from|in|of)\s+"
    r")\s+",
    re.I,
)

# Sub-topic suffixes that should merge into parent concept
_SUBTOPIC_SUFFIX = re.compile(
    r"\s+(?:prevention|detection|recovery|avoidance|handling|management|"
    r"scheduling|replacement|control|allocation|synchronization|deadlock)$",
    re.I,
)


@dataclass
class ExtractedTopic:
    topic: str
    canonical: str
    frequency: int
    frequently_asked: bool
    unit: str


def canonical_topic_name(topic: str) -> str:
    """Map variant phrasings to one syllabus topic title."""
    name = topic.strip()
    if not name:
        return name

    for _ in range(4):
        stripped = _TOPIC_VARIANT_PREFIX.sub("", name).strip()
        if not stripped or stripped.lower() == name.lower():
            break
        name = _title_case_topic(stripped)

    # "Deadlock Prevention" under "Deadlock" when both exist — handled in merge
    return _title_case_topic(name)


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _pick_parent(a: str, b: str, count_a: int, count_b: int) -> tuple[str, str]:
    """Return (parent, child) canonical names."""
    al, bl = a.lower(), b.lower()
    if al == bl:
        return a, b
    if al in bl and len(a) <= len(b):
        return a, b
    if bl in al and len(b) <= len(a):
        return b, a
    if count_a >= count_b:
        return a, b
    return b, a


def merge_similar_topics(counter: dict[str, int]) -> dict[str, int]:
    """
    Merge related topic strings into one comprehensive note topic.
    E.g. Virtual Memory + Advantages of Virtual Memory → Virtual Memory.
    """
    # First pass: canonicalize names and sum counts
    canonical_counts: dict[str, int] = defaultdict(int)
    display_name: dict[str, str] = {}

    for topic, count in counter.items():
        if not is_valid_topic(topic):
            continue
        canonical = canonical_topic_name(topic)
        if not is_valid_topic(canonical):
            continue
        key = canonical.lower()
        canonical_counts[key] += count
        # Prefer shorter canonical display when counts tie
        existing = display_name.get(key)
        if not existing or len(canonical) < len(existing):
            display_name[key] = canonical

    keys = list(canonical_counts.keys())
    absorb: dict[str, str] = {}

    for i, a in enumerate(keys):
        if a in absorb:
            continue
        for b in keys[i + 1 :]:
            if b in absorb:
                continue
            parent_key, child_key = _pick_parent(
                display_name[a], display_name[b], canonical_counts[a], canonical_counts[b]
            )
            pk, ck = parent_key.lower(), child_key.lower()
            if pk == ck:
                continue
            sim = _similarity(display_name[a], display_name[b])
            al, bl = a, b
            if al in bl or bl in al or sim >= 0.72:
                p, c = (al, bl) if canonical_counts[al] >= canonical_counts[bl] else (bl, al)
                absorb[c] = p

    merged: dict[str, int] = defaultdict(int)
    for key, count in canonical_counts.items():
        root = key
        while root in absorb:
            root = absorb[root]
        merged[display_name.get(root, display_name[key])] += count

    return dict(merged)


def extract_topics_from_questions(question_lines: list[str]) -> Counter[str]:
    """Extract academic concepts from cleaned question lines."""
    return extract_concepts_from_questions(question_lines)


def build_topic_records(merged: dict[str, int]) -> list[ExtractedTopic]:
    records: list[ExtractedTopic] = []
    for topic, freq in sorted(merged.items(), key=lambda x: -x[1]):
        records.append(
            ExtractedTopic(
                topic=topic,
                canonical=topic,
                frequency=freq,
                frequently_asked=freq >= 3,
                unit=assign_syllabus_unit(topic),
            )
        )
    return records


def topics_to_analysis_payload(
    records: list[ExtractedTopic],
    *,
    num_documents: int = 1,
    num_questions: int = 0,
) -> dict[str, Any]:
    """Build analysis-compatible dict from extracted topics."""
    if not records:
        return {}

    topic_frequency_table = [
        {
            "topic": r.topic,
            "unit": r.unit,
            "frequency": r.frequency,
            "frequently_asked": r.frequently_asked,
        }
        for r in records
    ]

    high = [r for r in topic_frequency_table if r["frequency"] >= 3]
    medium = [r for r in topic_frequency_table if r["frequency"] == 2]
    low = [r for r in topic_frequency_table if r["frequency"] == 1]

    topic_table = [
        {
            "topic": r["topic"],
            "frequency": r["frequency"],
            "importance": (
                "High" if r["frequency"] >= 3
                else "Medium" if r["frequency"] == 2
                else "Low"
            ),
            "frequently_asked": r.get("frequently_asked", False),
        }
        for r in topic_frequency_table
    ]

    max_freq = records[0].frequency
    groups: dict[str, list[str]] = defaultdict(list)
    for r in records:
        groups[r.unit].append(r.topic)

    return {
        "topic_frequency_table": topic_frequency_table,
        "topic_table": topic_table,
        "topic_frequency": {r.topic: r.frequency for r in records},
        "high_priority_topics": high,
        "medium_priority_topics": medium,
        "low_priority_topics": low,
        "predicted_important_topics": sorted(high + medium, key=lambda x: -x["frequency"]),
        "most_important_topics": high,
        "frequently_asked_topics": high + medium,
        "rarely_asked_topics": low,
        "syllabus_topics": [r.topic for r in records],
        "academic_topic_table": [{"topic": r.topic, "frequency": r.frequency} for r in records],
        "important_topics": [
            {
                "topic": r.topic,
                "score": round(r.frequency / max_freq, 2),
                "reason": (
                    "⭐ Frequently asked in exams"
                    if r.frequently_asked
                    else f"Asked {r.frequency} time(s)"
                ),
            }
            for r in records[:20]
        ],
        "topic_groups": [
            {"group": unit, "topics": topics}
            for unit, topics in sorted(groups.items(), key=lambda x: -len(x[1]))
        ],
        "repeated_questions": [],
        "exam_patterns": [],
        "summary": (
            f"Extracted {len(records)} unique topics from {num_questions} questions "
            f"across {num_documents} paper(s). "
            f"High priority: {len(high)}, Medium: {len(medium)}, Low: {len(low)}."
        ),
    }


def extract_and_merge_topics(
    question_lines: list[str],
    *,
    num_documents: int = 1,
) -> dict[str, Any]:
    raw_counter = extract_topics_from_questions(question_lines)
    if not raw_counter:
        return {}
    merged = merge_similar_topics(dict(raw_counter))
    records = build_topic_records(merged)
    return topics_to_analysis_payload(
        records,
        num_documents=num_documents,
        num_questions=len(question_lines),
    )
