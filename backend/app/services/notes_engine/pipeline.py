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
answers. Batches 2-11 then run concurrently (bounded) for speed.

On any batch failing validation after its one repair attempt, the whole
generation raises NotesSchemaError — there is no local template / fake-notes
fallback for Stage 3.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Awaitable, Callable

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

# Bounded concurrency for batches 2-11 — fast without hammering the provider.
DEFAULT_SECTION_CONCURRENCY = 3

# 11 focused calls per topic can trip a tight per-minute quota (esp. Gemini
# free-tier keys). Retry with backoff on rate-limit errors instead of failing
# the whole document — a transient 429 on one batch should not waste the 10
# batches that already succeeded.
_RATE_LIMIT_MAX_ATTEMPTS = 4
_RATE_LIMIT_BACKOFF_SECONDS = (12.0, 20.0, 35.0)
_RATE_LIMIT_PATTERN = re.compile(r"\b429\b|resource_exhausted|rate.?limit|quota", re.I)
_RETRY_DELAY_PATTERN = re.compile(r"retry in\s*([\d.]+)\s*s", re.I)


def _is_rate_limit_error(exc: BaseException) -> bool:
    return bool(_RATE_LIMIT_PATTERN.search(str(exc)))


def _suggested_retry_delay(exc: BaseException, *, attempt: int) -> float:
    match = _RETRY_DELAY_PATTERN.search(str(exc))
    if match:
        try:
            return float(match.group(1)) + 1.0
        except ValueError:
            pass
    idx = min(attempt - 1, len(_RATE_LIMIT_BACKOFF_SECONDS) - 1)
    return _RATE_LIMIT_BACKOFF_SECONDS[idx]


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
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Call one section batch, retrying with backoff ONLY on rate-limit errors."""
    attempt = 1
    while True:
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
