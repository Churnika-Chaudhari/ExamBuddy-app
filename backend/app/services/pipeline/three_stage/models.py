"""
Shared models for the ExamBuddy four-stage education pipeline.

Stages:
  1 — Extract topics from PYQs
  2 — Normalize to textbook terminology
  3 — Generate exam notes (Subject / Topic / Exam Priority only)
  4 — Generate quizzes from analysis + optional notes context
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Unified pipeline release identifier (stored in analysis/notes ai_metadata).
PIPELINE_VERSION = "edu_v21"


@dataclass
class TopicItem:
    name: str
    frequency: int = 1

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name.strip(), "frequency": max(1, int(self.frequency))}


@dataclass
class Stage1Result:
    """PYQ topic extraction only — never contains notes."""

    subject: str
    topics: list[TopicItem] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "topics": [t.as_dict() for t in self.topics],
        }


@dataclass
class Stage2Result:
    """Normalized textbook topic names — 1:1 with Stage 1, no invented topics."""

    subject: str
    topics: list[TopicItem] = field(default_factory=list)
    mapping: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "topics": [t.as_dict() for t in self.topics],
            "mapping": dict(self.mapping),
        }


def topics_from_dicts(rows: list[dict[str, Any]] | None) -> list[TopicItem]:
    out: list[TopicItem] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("topic") or "").strip()
        if not name:
            continue
        try:
            freq = int(row.get("frequency") or row.get("count") or 1)
        except (TypeError, ValueError):
            freq = 1
        out.append(TopicItem(name=name, frequency=max(1, freq)))
    return out
