"""Token estimation and structured logging helpers for notes generation."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("exambuddy.notes_engine")


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) for logging and budget checks."""
    if not text:
        return 0
    return max(1, len(text) // 4)


@dataclass
class NotesGenerationTrace:
    topic: str
    subject: str = ""
    stages: list[dict[str, Any]] = field(default_factory=list)
    started_at: float = field(default_factory=time.perf_counter)

    def mark(self, stage: str, **details: Any) -> None:
        payload = {"stage": stage, **details}
        self.stages.append(payload)
        logger.info(
            "notes_pipeline topic=%s stage=%s %s",
            self.topic,
            stage,
            " ".join(f"{k}={v}" for k, v in details.items()),
        )

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self.started_at) * 1000)

    def as_metadata(self) -> dict[str, Any]:
        return {
            "pipeline_stages": [s["stage"] for s in self.stages],
            "pipeline_elapsed_ms": self.elapsed_ms(),
            "pipeline_trace": self.stages[-8:],
        }
