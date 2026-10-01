"""
Lightweight performance timing for the PDF/analysis pipeline.

Temporary instrumentation added for the Stage 2 performance pass. Every timer
logs a single `[PERF]` line so results can be filtered from the logs.
Disable with EXAMBUDDY_PERF=0 (or false/no/off).
"""

from __future__ import annotations

import os
import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger("exambuddy.perf")

# Disable with EXAMBUDDY_PERF=0 (or false/no). Default is on.
PERF_ENABLED = os.environ.get("EXAMBUDDY_PERF", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}


def perf_mark(label: str, started: float, **fields: Any) -> float:
    """Log elapsed milliseconds since *started*. Returns elapsed ms."""
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if PERF_ENABLED:
        extra = " ".join(f"{k}={v}" for k, v in fields.items())
        logger.info("[PERF] %s: %.1fms%s", label, elapsed_ms, f" {extra}" if extra else "")
    return elapsed_ms


@contextmanager
def perf_timer(label: str, **fields: Any) -> Iterator[None]:
    """Context manager that logs `[PERF] <label>: <ms>` on exit."""
    started = time.perf_counter()
    try:
        yield
    finally:
        perf_mark(label, started, **fields)
