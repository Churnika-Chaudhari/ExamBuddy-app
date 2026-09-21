"""
Concise exam-notes pipeline (v40).

Flow:
  Subject + Topic
    -> ONE focused Gemini structured-JSON call (seven short sections)
    -> normalize + validate + render markdown
    -> on failure, ONE scoped repair call carrying the exact validation errors
    -> final document gate (headings, banned meta, 200-800 word band)

This replaces the v30 sectioned engine, which issued 11 batch calls paced
~14s apart to survive free-tier RPM limits while assembling a 2500+ word
chapter. With one (at most two) calls per topic that pacing is unnecessary;
only a bounded 429 retry remains.

There is no local-template fallback: if the model cannot produce valid notes,
the caller gets a structured error. The one exception is length — a note that
is complete and accurate but longer than the 600-word target is served (with
the overrun recorded in metadata) after the shorten-rewrite attempt, since
discarding correct notes over verbosity helps nobody.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

from app.core.exceptions import is_rate_limit_error, suggested_retry_delay_seconds
from app.services.notes_engine.markdown_formatter import (
    build_summary,
    extract_concise_payload,
    normalize_concise_payload,
    render_concise_markdown,
)
from app.services.notes_engine.prompt_builder import (
    build_concise_notes_prompts,
    build_concise_repair_prompts,
    clean_topic,
    is_unknown_topic_payload,
)
from app.services.notes_engine.schema import (
    CONCISE_ENGINE_ID,
    CONCISE_NOTES_RESPONSE_SCHEMA,
    CONCISE_PROMPT_VERSION,
    NOTES_MAX_OUTPUT_TOKENS,
    NOTES_TEMPERATURE,
)
from app.services.notes_engine.token_utils import NotesGenerationTrace
from app.services.notes_engine.validator import (
    NotesSchemaError,
    NotesValidationError,
    count_words,
    score_notes_quality,
    validate_concise_payload,
    validate_final_notes,
    word_count_status,
)

logger = logging.getLogger("exambuddy.notes_engine.pipeline")

# (system_prompt, user_prompt, response_schema, max_output_tokens, temperature) -> (json, metadata)
GenerateNotesJsonFn = Callable[
    [str, str, dict[str, Any], int, float], Awaitable[tuple[dict[str, Any], dict[str, Any]]]
]

# A 429 on a free-tier key is a per-minute-window error, so an instant retry
# lands in the same exhausted window. Wait out most of a window, but keep the
# attempt count bounded so a dead key fails in predictable time.
_RATE_LIMIT_MAX_ATTEMPTS = 3
_RATE_LIMIT_BACKOFF_SECONDS = (35.0, 60.0)


def _retry_delay(exc: BaseException, *, attempt: int) -> float:
    suggested = suggested_retry_delay_seconds(exc)
    if suggested is not None:
        return suggested + 1.0
    return _RATE_LIMIT_BACKOFF_SECONDS[min(attempt - 1, len(_RATE_LIMIT_BACKOFF_SECONDS) - 1)]


async def _call_with_rate_limit_retry(
    generate_notes_json: GenerateNotesJsonFn,
    system_prompt: str,
    user_prompt: str,
    *,
    topic: str,
    stage: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    attempt = 1
    while True:
        try:
            return await generate_notes_json(
                system_prompt,
                user_prompt,
                CONCISE_NOTES_RESPONSE_SCHEMA,
                NOTES_MAX_OUTPUT_TOKENS,
                NOTES_TEMPERATURE,
            )
        except Exception as exc:
            if attempt >= _RATE_LIMIT_MAX_ATTEMPTS or not is_rate_limit_error(exc):
                raise
            delay = _retry_delay(exc, attempt=attempt)
            logger.warning(
                "concise_notes rate-limited topic=%r stage=%s attempt=%d — retrying in %.1fs",
                topic,
                stage,
                attempt,
                delay,
            )
            await asyncio.sleep(delay)
            attempt += 1


class _Document:
    """A rendered note: structured payload, markdown, and its word count."""

    def __init__(self, structured: dict[str, Any], markdown: str, word_count: int) -> None:
        self.structured = structured
        self.markdown = markdown
        self.word_count = word_count


class ConciseNotesPipeline:
    """Stage-3 engine: one focused Gemini call -> validated 7-section note."""

    engine_id = CONCISE_ENGINE_ID
    prompt_version = CONCISE_PROMPT_VERSION

    async def run(
        self,
        *,
        topic: str,
        subject: str | None = None,
        generate_notes_json: GenerateNotesJsonFn,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        clean = clean_topic(topic) or (topic or "").strip()
        subject_name = (subject or "General").strip() or "General"
        trace = NotesGenerationTrace(topic=clean, subject=subject_name)

        system_prompt, user_prompt = build_concise_notes_prompts(
            topic=clean, subject=subject_name
        )
        logger.info("concise_notes start topic=%r subject=%r", clean, subject_name)
        trace.mark("generate", attempt=1)
        raw, provider_meta = await _call_with_rate_limit_retry(
            generate_notes_json, system_prompt, user_prompt, topic=clean, stage="generate"
        )
        logger.info("concise_notes response topic=%r preview=%r", clean, str(raw)[:400])

        if is_unknown_topic_payload(raw):
            trace.mark("validate", ok=False, error="UNKNOWN_TOPIC")
            raise NotesValidationError(
                f"UNKNOWN_TOPIC: '{clean}' is not a teachable engineering topic",
                code="UNKNOWN_TOPIC",
                details=[{"field": "topic", "error": "UNKNOWN_TOPIC"}],
            )

        calls = 1
        repaired = False
        overrun = False

        try:
            document = self._build_document(raw, topic=clean, subject=subject_name)
            trace.mark("validate", ok=True, attempt=1, word_count=document.word_count)
        except NotesValidationError as first_error:
            trace.mark("validate", ok=False, attempt=1, error=str(first_error))
            logger.warning(
                "concise_notes validation failed topic=%r — repairing once: %s (%s)",
                clean,
                first_error,
                first_error.details,
            )
            document, provider_meta, overrun = await self._repair(
                raw,
                first_error,
                topic=clean,
                subject=subject_name,
                generate_notes_json=generate_notes_json,
                trace=trace,
                provider_meta=provider_meta,
            )
            calls = 2
            repaired = True

        quality = score_notes_quality(document.structured, document.markdown)
        length_status = word_count_status(document.word_count)
        logger.info(
            "concise_notes ok topic=%r subject=%r word_count=%d chars=%d calls=%d repaired=%s length=%s",
            clean,
            subject_name,
            document.word_count,
            len(document.markdown),
            calls,
            repaired,
            length_status,
        )

        metadata = dict(provider_meta or {})
        metadata.update(
            {
                "prompt_version": CONCISE_PROMPT_VERSION,
                "notes_engine": CONCISE_ENGINE_ID,
                "generation_mode": "ai_concise",
                "structured_json_mode": True,
                "gemini_calls": calls,
                "repaired": repaired,
                "word_count": document.word_count,
                "word_count_status": length_status,
                "word_count_over_limit": overrun,
                "quality": quality,
            }
        )
        metadata.update(trace.as_metadata())

        result = {
            "notes": document.markdown,
            "summary": build_summary(document.structured) or None,
            "structured": extract_concise_payload(document.structured),
            "word_count": document.word_count,
        }
        return result, metadata

    def _build_document(
        self, raw: dict[str, Any], *, topic: str, subject: str
    ) -> _Document:
        """Normalize -> validate sections -> render -> validate document."""
        structured = normalize_concise_payload(raw, topic=topic)
        structured["topic"] = structured.get("topic") or topic
        structured["subject"] = subject

        validate_concise_payload(structured, topic=topic)
        markdown = render_concise_markdown(structured)
        word_count = count_words(markdown)
        validate_final_notes(markdown, structured, word_count=word_count)
        return _Document(structured, markdown, word_count)

    async def _repair(
        self,
        draft: dict[str, Any],
        first_error: NotesValidationError,
        *,
        topic: str,
        subject: str,
        generate_notes_json: GenerateNotesJsonFn,
        trace: NotesGenerationTrace,
        provider_meta: dict[str, Any],
    ) -> tuple[_Document, dict[str, Any], bool]:
        """One scoped rewrite. Returns (document, provider_meta, overran_length)."""
        errors = list(first_error.details or []) or [{"error": str(first_error)}]
        repair_system, repair_user = build_concise_repair_prompts(
            topic=topic, subject=subject, errors=errors, draft=draft
        )
        trace.mark("generate", attempt=2, repair=True)
        raw, repair_meta = await _call_with_rate_limit_retry(
            generate_notes_json, repair_system, repair_user, topic=topic, stage="repair"
        )
        provider_meta = repair_meta or provider_meta

        try:
            document = self._build_document(raw, topic=topic, subject=subject)
        except NotesValidationError as exc:
            # Verbosity alone is not worth failing the request: if everything
            # else passed, keep the longer note and flag the overrun.
            if exc.code == "NOTES_TOO_LONG":
                structured = normalize_concise_payload(raw, topic=topic)
                structured["topic"] = structured.get("topic") or topic
                structured["subject"] = subject
                markdown = render_concise_markdown(structured)
                word_count = count_words(markdown)
                trace.mark("validate", ok=True, attempt=2, repaired=True, over_limit=word_count)
                logger.warning(
                    "concise_notes still over the word limit after repair topic=%r word_count=%d — serving anyway",
                    topic,
                    word_count,
                )
                return _Document(structured, markdown, word_count), provider_meta, True

            trace.mark("validate", ok=False, attempt=2, error=str(exc))
            raise NotesSchemaError(
                f"Notes for '{topic}' failed validation after one repair attempt",
                details=[*errors, *(exc.details or [{"error": str(exc)}])],
            ) from exc

        trace.mark("validate", ok=True, attempt=2, repaired=True, word_count=document.word_count)
        logger.info("concise_notes repaired topic=%r word_count=%d", topic, document.word_count)
        return document, provider_meta, False


async def generate_concise_notes_result(
    *,
    topic: str,
    subject: str | None = None,
    generate_notes_json: GenerateNotesJsonFn,
) -> tuple[dict[str, Any], dict[str, Any]]:
    return await ConciseNotesPipeline().run(
        topic=topic,
        subject=subject,
        generate_notes_json=generate_notes_json,
    )


__all__ = [
    "ConciseNotesPipeline",
    "GenerateNotesJsonFn",
    "generate_concise_notes_result",
]
