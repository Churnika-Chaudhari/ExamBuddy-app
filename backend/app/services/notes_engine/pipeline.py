"""
Sectioned Exam Notes Pipeline (v30) — NotebookLM-style multi-call orchestrator.

CRITICAL DESIGN RULE: a full chapter is NEVER produced in one LLM call.

Flow:
  Topic → 11 focused section batches (see schema.SECTION_ORDER), each with its
  own compact responseSchema → per-batch validate (+ single scoped repair on
  failure) → merge into one structured dict → render ONE long-form markdown
  document covering every required heading → final quality/heading/word-count
  gate.

Batch 1 ("topic_definition_intro") runs first and alone: it both gates
UNKNOWN_TOPIC refusals and seeds a short context recap fed to every later
batch so the document reads as one coherent chapter rather than 11 disjoint
answers. Batches 2-11 then run with DEFAULT_SECTION_CONCURRENCY (1 by
default, free-tier friendly) and a minimum inter-call spacing so the 11
calls/topic stay under typical Gemini free-tier rate limits (~5 RPM).

On any batch failing validation after its one repair attempt, the whole
generation raises NotesSchemaError — there is no local template / fake-notes
fallback for Stage 3.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable

from app.core.exceptions import is_rate_limit_error, suggested_retry_delay_seconds
from app.services.notes_engine.markdown_formatter import render_sectioned_markdown
from app.services.notes_engine.prompt_builder import (
    build_context_recap,
    build_section_prompts,
    build_section_repair_prompt,
    is_unknown_topic_payload,
    normalize_exam_priority,
)
from app.services.notes_engine.schema import (
    SECTION_MAX_OUTPUT_TOKENS,
    SECTION_ORDER,
    SECTION_SCHEMAS,
    SECTION_TEMPERATURE,
    SECTION_TITLES,
    SECTIONED_ENGINE_ID,
    SECTIONED_PROMPT_VERSION,
)
from app.services.notes_engine.token_utils import NotesGenerationTrace
from app.services.notes_engine.validator import (
    NotesSchemaError,
    NotesValidationError,
    count_words,
    validate_final_notes,
    validate_section_payload,
)

logger = logging.getLogger("exambuddy.notes_engine.pipeline")

# (system_prompt, user_prompt, response_schema, max_output_tokens, temperature) -> (json, metadata)
GenerateSectionJsonFn = Callable[
    [str, str, dict[str, Any], int, float], Awaitable[tuple[dict[str, Any], dict[str, Any]]]
]

# Bounded concurrency for batches 2-11. Gemini FREE-TIER keys allow only
# ~5 requests/minute — 11 section calls at any concurrency > 1 blows past
# that almost immediately. Keep this at 1 (fully sequential) unless you know
# your key has a paid-tier quota; see SECTION_CALL_MIN_SPACING_SECONDS below
# for the actual pacing that keeps free-tier keys under quota.
DEFAULT_SECTION_CONCURRENCY = 1

# Minimum spacing enforced between the START of consecutive Gemini section
# calls (across the whole pipeline run, regardless of concurrency). Gemini
# free tier is ~5 requests/minute (12s/call); 14s of headroom keeps 11
# sequential section calls (~2.5 min/topic) comfortably under that even
# before any 429 backoff kicks in.
SECTION_CALL_MIN_SPACING_SECONDS = 14.0

# 11 focused calls per topic can trip a tight per-minute quota (esp. Gemini
# free-tier keys). Retry with backoff on rate-limit errors instead of failing
# the whole document — a transient 429 on one batch should not waste the 10
# batches that already succeeded.
#
# Free-tier 429s are per-minute-window errors, not instant-retry errors —
# backing off 12-35s (the old values) routinely retries into the SAME
# still-exhausted window. 55-70s comfortably clears a full RPM window before
# retrying, and only 3 attempts are made (2 backoff waits) so a truly dead
# key/quota still fails in a bounded time instead of hanging the request.
_RATE_LIMIT_MAX_ATTEMPTS = 3
_RATE_LIMIT_BACKOFF_SECONDS = (55.0, 70.0)


def _is_rate_limit_error(exc: BaseException) -> bool:
    # Checks exc AND its __cause__ chain — the real 429/quota text usually
    # lives on the wrapped provider exception, not the outer generic
    # "AI generation failed for all configured providers" message.
    return is_rate_limit_error(exc)


def _suggested_retry_delay(exc: BaseException, *, attempt: int) -> float:
    delay = suggested_retry_delay_seconds(exc)
    if delay is not None:
        return delay + 1.0
    idx = min(attempt - 1, len(_RATE_LIMIT_BACKOFF_SECONDS) - 1)
    return _RATE_LIMIT_BACKOFF_SECONDS[idx]


class _SectionCallPacer:
    """
    Enforces a minimum spacing between the start of consecutive Gemini
    section calls, independent of the concurrency semaphore — a cheap,
    dependency-free way to stay under a free-tier requests-per-minute quota
    even if concurrency is ever raised above 1.
    """

    def __init__(self, min_spacing_seconds: float) -> None:
        self._min_spacing = min_spacing_seconds
        self._lock = asyncio.Lock()
        self._last_call_at: float | None = None

    async def wait_turn(self, *, section_id: str = "", topic: str = "") -> None:
        async with self._lock:
            now = time.monotonic()
            if self._last_call_at is not None:
                remaining = self._min_spacing - (now - self._last_call_at)
                if remaining > 0:
                    # Visible in Render logs so slow Stage-3 generations are
                    # clearly explained (free-tier pacing), not mistaken for
                    # a hang.
                    logger.info(
                        "notes_section pacing topic=%r section=%s waiting %.1fs before next Gemini call (free-tier RPM)",
                        topic,
                        section_id,
                        remaining,
                    )
                    await asyncio.sleep(remaining)
            self._last_call_at = time.monotonic()


async def _call_with_rate_limit_retry(
    generate_section_json: GenerateSectionJsonFn,
    system_prompt: str,
    user_prompt: str,
    schema: dict[str, Any],
    max_tokens: int,
    temperature: float,
    *,
    section_id: str,
    topic: str,
    pacer: _SectionCallPacer,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Call one section batch, retrying with backoff ONLY on rate-limit errors."""
    attempt = 1
    while True:
        await pacer.wait_turn(section_id=section_id, topic=topic)
        try:
            return await generate_section_json(system_prompt, user_prompt, schema, max_tokens, temperature)
        except Exception as exc:
            if attempt >= _RATE_LIMIT_MAX_ATTEMPTS or not _is_rate_limit_error(exc):
                raise
            delay = _suggested_retry_delay(exc, attempt=attempt)
            logger.warning(
                "notes_section rate-limited topic=%r section=%s attempt=%d — retrying in %.1fs",
                topic,
                section_id,
                attempt,
                delay,
            )
            await asyncio.sleep(delay)
            attempt += 1


class SectionedNotesPipeline:
    """Production Stage-3 exam-notes pipeline — sectioned, multi-call, merged."""

    def __init__(self, *, concurrency: int = DEFAULT_SECTION_CONCURRENCY) -> None:
        self.concurrency = max(1, concurrency)
        self._pacer = _SectionCallPacer(SECTION_CALL_MIN_SPACING_SECONDS)

    async def _run_section(
        self,
        section_id: str,
        *,
        topic: str,
        subject: str | None,
        exam_priority: str,
        context_recap: str,
        generate_section_json: GenerateSectionJsonFn,
        trace: NotesGenerationTrace,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        schema = SECTION_SCHEMAS[section_id]
        max_tokens = SECTION_MAX_OUTPUT_TOKENS[section_id]
        temperature = SECTION_TEMPERATURE.get(section_id, 0.35)
        title = SECTION_TITLES.get(section_id, section_id)

        system_prompt, user_prompt = build_section_prompts(
            section_id,
            topic=topic,
            subject=subject,
            exam_priority=exam_priority,
            context_recap=context_recap,
        )

        trace.mark("section_generate", section=section_id, title=title, attempt=1)
        logger.info(
            "notes_section start topic=%r section=%s attempt=1 user_preview=%r",
            topic,
            section_id,
            user_prompt[-300:],
        )
        try:
            raw, meta = await _call_with_rate_limit_retry(
                generate_section_json,
                system_prompt,
                user_prompt,
                schema,
                max_tokens,
                temperature,
                section_id=section_id,
                topic=topic,
                pacer=self._pacer,
            )
        except Exception as exc:
            trace.mark("section_generate_error", section=section_id, attempt=1, error=str(exc)[:200])
            logger.error("notes_section generate failed topic=%r section=%s: %s", topic, section_id, exc)
            raise

        # Batch 1 may legitimately refuse via UNKNOWN_TOPIC — never repair that.
        if section_id == "topic_definition_intro" and is_unknown_topic_payload(raw):
            return raw, meta

        first_error: NotesValidationError | None = None
        try:
            validate_section_payload(section_id, raw)
            trace.mark("section_validate", section=section_id, ok=True, attempt=1)
            logger.info(
                "notes_section ok topic=%r section=%s attempt=1 keys=%s",
                topic,
                section_id,
                list(raw.keys()),
            )
            return raw, meta
        except NotesValidationError as exc:
            first_error = exc
            trace.mark("section_validate", section=section_id, ok=False, attempt=1, error=str(exc))
            logger.warning(
                "notes_section validation failed topic=%r section=%s — repairing once: %s",
                topic,
                section_id,
                exc,
            )

        assert first_error is not None
        first_error_details = list(first_error.details or [])
        repair_system, repair_user = build_section_repair_prompt(
            section_id,
            topic=topic,
            subject=subject,
            exam_priority=exam_priority,
            errors=first_error_details or [str(first_error)],
            draft=raw,
        )
        trace.mark("section_generate", section=section_id, attempt=2, repair=True)
        try:
            raw2, meta2 = await _call_with_rate_limit_retry(
                generate_section_json,
                repair_system,
                repair_user,
                schema,
                max_tokens,
                temperature,
                section_id=section_id,
                topic=topic,
                pacer=self._pacer,
            )
            validate_section_payload(section_id, raw2)
            trace.mark("section_validate", section=section_id, ok=True, attempt=2, repaired=True)
            logger.info("notes_section repaired topic=%r section=%s attempt=2", topic, section_id)
            return raw2, meta2
        except Exception as exc2:
            trace.mark("section_generate_error", section=section_id, attempt=2, error=str(exc2)[:200])
            logger.error(
                "notes_section failed after repair topic=%r section=%s: %s", topic, section_id, exc2
            )
            raise NotesSchemaError(
                f"Section '{title}' failed validation after one repair attempt",
                details=[
                    {"section": section_id, "title": title, "error": str(exc2)[:300]},
                    *first_error_details,
                ],
            ) from exc2

    async def run(
        self,
        *,
        topic: str,
        subject: str | None,
        exam_priority: str,
        generate_section_json: GenerateSectionJsonFn,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        trace = NotesGenerationTrace(topic=topic, subject=subject or "")
        priority = normalize_exam_priority(exam_priority)

        # Batch 1 runs alone — it seeds context recap + gates UNKNOWN_TOPIC.
        seed, seed_meta = await self._run_section(
            "topic_definition_intro",
            topic=topic,
            subject=subject,
            exam_priority=priority,
            context_recap="",
            generate_section_json=generate_section_json,
            trace=trace,
        )
        if is_unknown_topic_payload(seed):
            trace.mark("validate", ok=False, error="UNKNOWN_TOPIC")
            raise NotesValidationError(
                f"UNKNOWN_TOPIC: '{topic}' is too ambiguous for textbook notes",
                code="UNKNOWN_TOPIC",
                details=[{"field": "topic", "error": "UNKNOWN_TOPIC"}],
            )

        structured: dict[str, Any] = {k: v for k, v in seed.items() if k != "status"}
        provider_meta = dict(seed_meta or {})
        context_recap = build_context_recap(structured, topic=topic)

        remaining = [s for s in SECTION_ORDER if s != "topic_definition_intro"]
        semaphore = asyncio.Semaphore(self.concurrency)

        async def _worker(section_id: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
            async with semaphore:
                data, meta = await self._run_section(
                    section_id,
                    topic=topic,
                    subject=subject,
                    exam_priority=priority,
                    context_recap=context_recap,
                    generate_section_json=generate_section_json,
                    trace=trace,
                )
                return section_id, data, meta

        results = await asyncio.gather(*[_worker(section_id) for section_id in remaining])
        for section_id, data, meta in results:
            structured.update(data)
            if meta:
                provider_meta = meta

        structured["topic"] = structured.get("topic") or topic
        structured["subject"] = subject or "General"
        structured["exam_priority"] = priority

        markdown = render_sectioned_markdown(structured)
        word_count = count_words(markdown)
        trace.mark("assemble", word_count=word_count, chars=len(markdown), sections=len(SECTION_ORDER))
        logger.info(
            "notes_pipeline assembled topic=%r subject=%r word_count=%d chars=%d",
            topic,
            subject,
            word_count,
            len(markdown),
        )

        validate_final_notes(markdown, structured, word_count=word_count)
        trace.mark("validate", ok=True, word_count=word_count)

        quality = {
            "word_count": word_count,
            "chars": len(markdown),
            "sections_completed": len(SECTION_ORDER),
            "has_diagram": bool(structured.get("diagram")),
            "viva_count": len(structured.get("viva") or []),
            "interview_count": len(structured.get("interview") or []),
        }

        meta = dict(provider_meta)
        meta.update(
            {
                "prompt_version": SECTIONED_PROMPT_VERSION,
                "notes_engine": SECTIONED_ENGINE_ID,
                "structured_json_mode": True,
                "generation_mode": "ai_sectioned",
                "word_count": word_count,
                "quality": quality,
                "section_count": len(SECTION_ORDER),
            }
        )
        meta.update(trace.as_metadata())

        result = {
            "notes": markdown,
            "summary": structured.get("summary"),
            "structured": structured,
            "word_count": word_count,
        }
        return result, meta


async def generate_sectioned_notes_result(
    *,
    topic: str,
    subject: str | None,
    exam_priority: str,
    generate_section_json: GenerateSectionJsonFn,
    concurrency: int = DEFAULT_SECTION_CONCURRENCY,
) -> tuple[dict[str, Any], dict[str, Any]]:
    pipeline = SectionedNotesPipeline(concurrency=concurrency)
    return await pipeline.run(
        topic=topic,
        subject=subject,
        exam_priority=exam_priority,
        generate_section_json=generate_section_json,
    )
