"""Shared helpers for reading normalized topics from analysis documents."""

from __future__ import annotations

from typing import Any

from app.utils.topic_extractor import filter_topics


def topics_from_analysis_doc(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Collect syllabus topics from a completed analysis document.

    Used by quiz (Stage 4), subject stats, and analysis post-processing.
    """
    seen: set[str] = set()
    topics: list[dict[str, Any]] = []

    def add(
        topic: str,
        *,
        unit: str | None = None,
        frequency: int = 1,
        importance: str | None = None,
    ) -> None:
        t = topic.strip()
        if not t or t.lower() in seen:
            return
        if not filter_topics([t]):
            return
        seen.add(t.lower())
        topics.append(
            {
                "topic": t,
                "unit": unit,
                "frequency": frequency,
                "importance": importance,
            }
        )

    for row in analysis.get("topic_frequency_table") or []:
        if isinstance(row, dict):
            add(
                row.get("topic", ""),
                unit=row.get("unit"),
                frequency=int(row.get("frequency") or 1),
                importance=row.get("importance"),
            )

    for bucket, importance in (
        ("high_priority_topics", "High"),
        ("medium_priority_topics", "Medium"),
        ("low_priority_topics", "Low"),
        ("most_important_topics", "High"),
        ("frequently_asked_topics", "Medium"),
        ("rarely_asked_topics", "Low"),
    ):
        for row in analysis.get(bucket) or []:
            if isinstance(row, dict):
                add(
                    row.get("topic", ""),
                    unit=row.get("unit"),
                    frequency=int(row.get("frequency") or 1),
                    importance=importance,
                )

    for row in analysis.get("important_topics") or []:
        if isinstance(row, dict):
            add(row.get("topic", ""), frequency=1)

    freq = analysis.get("topic_frequency") or {}
    if isinstance(freq, dict):
        for topic, count in sorted(freq.items(), key=lambda x: x[1], reverse=True):
            add(str(topic), frequency=int(count or 1))

    for topic in analysis.get("syllabus_topics") or []:
        if isinstance(topic, str):
            add(topic)

    topics.sort(key=lambda x: x.get("frequency", 0), reverse=True)
    return topics
