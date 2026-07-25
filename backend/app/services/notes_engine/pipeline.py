"""
Exam Notes Pipeline orchestrator.

Stages:
  prepare → generate (structured JSON) → schema validate → format → quality validate
  On validation failure: one repair prompt, then structured error.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable

from app.services.notes_engine.markdown_formatter import (
    extract_exam_payload,
    format_exam_notes_markdown,
    is_exam_notes_result,
)
from app.services.notes_engine.prompt_builder import (
    build_exam_notes_prompts,
    build_notes_repair_prompts,
    is_unknown_topic_payload,
)
from app.services.notes_engine.schema import PROMPT_VERSION
from app.services.notes_engine.token_utils import NotesGenerationTrace, estimate_tokens
from app.services.notes_engine.validator import (
    NotesSchemaError,
    NotesValidationError,
    deduplicate_structured_notes,
    score_notes_quality,
    validate_exam_notes,
    validate_exam_notes_schema,
)

logger = logging.getLogger("exambuddy.notes_engine.pipeline")

GenerateJsonFn = Callable[[str, str], Awaitable[tuple[dict[str, Any], dict[str, Any]]]]


class ExamNotesPipeline:
    """Production exam-notes generation pipeline."""

    def __init__(self, *, max_retries: int = 1) -> None:
        # max_retries kept for API compatibility; repair is always at most once.
        self.max_retries = max(1, max_retries)

    def prepare_context(
        self,
        *,
        topic: str,
        rag_context: str = "",
        analysis_context: str = "",
        subject: str | None = None,
        exam_priority: str = "",
        pyq_questions: str = "",
        pipeline_context: str = "",
    ) -> dict[str, Any]:
        trace = NotesGenerationTrace(topic=topic, subject=subject or "")
        # Stage 3: never inject PYQ/RAG/pipeline text into prompts.
        _ = (rag_context, analysis_context, pyq_questions, pipeline_context)
        prepared = {"rag_context": "", "chunk_count": 0}
        trace.mark("chunk", chunks=0, context_tokens=0, stage3_isolated=True)

        system_prompt, user_prompt = build_exam_notes_prompts(
            topic=topic,
            subject=subject,
            exam_priority=exam_priority,
        )
        logger.info(
            "Stage3 prompt ready topic=%r subject=%r exam_priority=%s system_tokens~%d user=%r",
            topic,
            subject,
            exam_priority,
            estimate_tokens(system_prompt),
            user_prompt,
        )
        trace.mark(
            "prompt",
            system_tokens=estimate_tokens(system_prompt),
            user_tokens=estimate_tokens(user_prompt),
            user_fields="subject,topic,exam_priority",
        )

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "prepared": prepared,
            "trace": trace,
            "subject": subject,
            "exam_priority": exam_priority,
        }

    def postprocess(
        self,
        raw: dict[str, Any],
        *,
        topic: str,
        trace: NotesGenerationTrace | None = None,
        skip_schema: bool = False,
    ) -> dict[str, Any]:
        """Schema validate → dedupe → format → quality validate."""
        active_trace = trace or NotesGenerationTrace(topic=topic)
        structured = dict(raw or {})
        if topic and not structured.get("topic"):
            structured["topic"] = topic

        if not skip_schema:
            validate_exam_notes_schema(structured)
            active_trace.mark("schema_validate", ok=True)

        if is_unknown_topic_payload(structured):
            active_trace.mark("validate", ok=False, error="UNKNOWN_TOPIC")
            raise NotesValidationError(
                f"UNKNOWN_TOPIC: '{topic}' is too ambiguous for textbook notes",
                code="UNKNOWN_TOPIC",
                details=[{"field": "topic", "error": "UNKNOWN_TOPIC"}],
            )

        if not is_exam_notes_result(structured) and structured.get("notes"):
            # Plain markdown fallback path
            markdown = str(structured.get("notes") or "").strip()
            active_trace.mark("format", mode="plain_markdown", chars=len(markdown))
            validate_exam_notes({"definition": "n/a"}, markdown=markdown)
            return {
                "notes": markdown,
                "summary": structured.get("summary"),
                "structured": None,
                "quality": {"chars": len(markdown)},
                "trace": active_trace,
            }

        structured = deduplicate_structured_notes(structured)
        active_trace.mark("dedupe")

        payload = extract_exam_payload(structured)
        markdown = format_exam_notes_markdown(payload or structured)
        active_trace.mark("format", mode="exam_structured", chars=len(markdown))

        validate_exam_notes(payload or structured, markdown=markdown)
        active_trace.mark("validate", ok=True)

        quality = score_notes_quality(payload or structured, markdown)
        summary_bits = None
        if payload:
            summary_bits = payload.get("revisionSummary") or payload.get("revisionSheet")
        if isinstance(summary_bits, list):
            summary = " • ".join(str(b) for b in summary_bits[:6])
        else:
            summary = structured.get("summary")

        return {
            "notes": markdown,
            "summary": summary,
            "structured": payload,
            "quality": quality,
            "trace": active_trace,
        }

    async def run(
        self,
        *,
        topic: str,
        generate_json: GenerateJsonFn,
        rag_context: str = "",
        analysis_context: str = "",
        subject: str | None = None,
        exam_priority: str = "",
        pyq_questions: str = "",
        pipeline_context: str = "",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Execute pipeline: generate → validate → (optional one repair) → finalize.

        On schema/quality failure after repair, raises NotesSchemaError with details
        (structured backend error — never returns malformed JSON).
        """
        prep = self.prepare_context(
            topic=topic,
            rag_context=rag_context,
            analysis_context=analysis_context,
            subject=subject,
            exam_priority=exam_priority,
            pyq_questions=pyq_questions,
            pipeline_context=pipeline_context,
        )
        trace: NotesGenerationTrace = prep["trace"]

        trace.mark("generate", attempt=1)
        try:
            raw, metadata = await generate_json(prep["system_prompt"], prep["user_prompt"])
        except Exception as exc:
            logger.error("Notes generation failed topic=%s: %s", topic, exc)
            trace.mark("generate_error", attempt=1, error=str(exc)[:200])
            raise

        first_error: NotesValidationError | None = None
        try:
            processed = self.postprocess(raw, topic=topic, trace=trace)
            return self._finalize(processed, metadata, prep, attempt=1, repaired=False)
        except NotesValidationError as exc:
            if exc.code == "UNKNOWN_TOPIC" or "UNKNOWN_TOPIC" in str(exc):
                raise
            first_error = exc
            logger.warning(
                "Notes validation failed topic=%s — attempting one repair: %s",
                topic,
                exc,
            )
            trace.mark("validate", ok=False, error=str(exc), attempt=1, code=exc.code)

        assert first_error is not None
        # One repair attempt with a dedicated repair prompt.
        repair_system, repair_user = build_notes_repair_prompts(
            topic=topic,
            subject=prep.get("subject") or subject,
            exam_priority=prep.get("exam_priority") or exam_priority,
            errors=first_error.details or [str(first_error)],
            draft=raw if isinstance(raw, dict) else {},
        )
        trace.mark("generate", attempt=2, repair=True)
        try:
            raw2, metadata2 = await generate_json(repair_system, repair_user)
        except Exception as repair_exc:
            logger.error("Notes repair generation failed topic=%s: %s", topic, repair_exc)
            raise NotesSchemaError(
                "AI notes repair call failed",
                details=[
                    {"reason": "NOTES_REPAIR_FAILED", "error": str(repair_exc)[:300]},
                    *list(first_error.details or []),
                ],
            ) from repair_exc

        try:
            # Re-validate schema before parsing/formatting.
            validate_exam_notes_schema(raw2)
            processed = self.postprocess(raw2, topic=topic, trace=trace, skip_schema=True)
            return self._finalize(processed, metadata2, prep, attempt=2, repaired=True)
        except NotesValidationError as repair_validation_error:
            if (
                repair_validation_error.code == "UNKNOWN_TOPIC"
                or "UNKNOWN_TOPIC" in str(repair_validation_error)
            ):
                raise
            details = list(repair_validation_error.details or [])
            if not details:
                details = [{"error": str(repair_validation_error)}]
            details.insert(
                0,
                {
                    "reason": "NOTES_SCHEMA_INVALID",
                    "attempt": 2,
                    "repair_attempted": True,
                    "code": repair_validation_error.code,
                },
            )
            logger.error(
                "Notes validation failed after repair topic=%s: %s",
                topic,
                repair_validation_error,
            )
            raise NotesSchemaError(
                "AI returned invalid notes JSON after repair",
                details=details,
            ) from repair_validation_error

    def _finalize(
        self,
        processed: dict[str, Any],
        metadata: dict[str, Any] | None,
        prep: dict[str, Any],
        *,
        attempt: int,
        repaired: bool,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        meta = dict(metadata or {})
        meta["prompt_version"] = PROMPT_VERSION
        meta["attempt"] = attempt
        meta["repair_attempted"] = repaired
        meta["notes_engine"] = "exambuddy_edu_v21"
        meta["structured_json_mode"] = True
        meta["quality"] = processed["quality"]
        meta.update(prep["trace"].as_metadata())
        meta["rag_chunk_count"] = prep["prepared"]["chunk_count"]
        return {
            "notes": processed["notes"],
            "summary": processed["summary"],
            "structured": processed["structured"],
        }, meta


async def generate_exam_notes_result(
    *,
    topic: str,
    generate_json: GenerateJsonFn,
    rag_context: str = "",
    analysis_context: str = "",
    subject: str | None = None,
    exam_priority: str = "",
    pyq_questions: str = "",
    pipeline_context: str = "",
    max_retries: int = 1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    pipeline = ExamNotesPipeline(max_retries=max_retries)
    return await pipeline.run(
        topic=topic,
        generate_json=generate_json,
        rag_context=rag_context,
        analysis_context=analysis_context,
        subject=subject,
        exam_priority=exam_priority,
        pyq_questions=pyq_questions,
        pipeline_context=pipeline_context,
    )
