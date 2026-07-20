"""
Exam Notes Pipeline orchestrator.

Stages:
  clean → chunk → prompt → generate → dedupe → format → validate → finalize
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable

from app.services.notes_engine.chunking import prepare_topic_context
from app.services.notes_engine.markdown_formatter import (
    extract_exam_payload,
    format_exam_notes_markdown,
    is_exam_notes_result,
)
from app.services.notes_engine.prompt_builder import (
    build_exam_notes_prompts,
    pipeline_instructions,
)
from app.services.notes_engine.schema import PROMPT_VERSION
from app.services.notes_engine.token_utils import NotesGenerationTrace, estimate_tokens
from app.services.notes_engine.validator import (
    NotesValidationError,
    deduplicate_structured_notes,
    score_notes_quality,
    validate_exam_notes,
)

logger = logging.getLogger("exambuddy.notes_engine.pipeline")

GenerateJsonFn = Callable[[str, str], Awaitable[tuple[dict[str, Any], dict[str, Any]]]]


class ExamNotesPipeline:
    """Production exam-notes generation pipeline."""

    def __init__(self, *, max_retries: int = 2) -> None:
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
        prepared = prepare_topic_context(rag_context, topic=topic)
        trace.mark(
            "chunk",
            chunks=prepared["chunk_count"],
            context_tokens=estimate_tokens(prepared["rag_context"]),
        )

        merged_pipeline = "\n".join(
            p for p in [pipeline_context.strip(), pipeline_instructions(subject=subject)] if p
        ).strip()

        system_prompt, user_prompt = build_exam_notes_prompts(
            topic=topic,
            subject=subject,
            rag_context=prepared["rag_context"] or rag_context,
            analysis_context=analysis_context,
            pipeline_context=merged_pipeline,
            exam_priority=exam_priority,
            pyq_questions=pyq_questions,
        )
        trace.mark(
            "prompt",
            system_tokens=estimate_tokens(system_prompt),
            user_tokens=estimate_tokens(user_prompt),
        )

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "prepared": prepared,
            "trace": trace,
        }

    def postprocess(
        self,
        raw: dict[str, Any],
        *,
        topic: str,
        trace: NotesGenerationTrace | None = None,
    ) -> dict[str, Any]:
        """Dedupe → format → validate structured LLM output."""
        active_trace = trace or NotesGenerationTrace(topic=topic)
        structured = dict(raw or {})
        if topic and not structured.get("topic"):
            structured["topic"] = topic

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
        summary_bits = payload.get("thirtySecondRevision") if payload else None
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
        Execute full pipeline with retries.

        Returns (result, metadata) where result has notes/summary/structured.
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
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                trace.mark("generate", attempt=attempt)
                raw, metadata = await generate_json(prep["system_prompt"], prep["user_prompt"])
                processed = self.postprocess(raw, topic=topic, trace=trace)
                metadata = dict(metadata or {})
                metadata["prompt_version"] = PROMPT_VERSION
                metadata["attempt"] = attempt
                metadata["notes_engine"] = "exam_v17"
                metadata["quality"] = processed["quality"]
                metadata.update(trace.as_metadata())
                metadata["rag_chunk_count"] = prep["prepared"]["chunk_count"]
                return {
                    "notes": processed["notes"],
                    "summary": processed["summary"],
                    "structured": processed["structured"],
                }, metadata
            except NotesValidationError as exc:
                last_exc = exc
                logger.warning(
                    "Notes validation failed topic=%s attempt=%s: %s",
                    topic,
                    attempt,
                    exc,
                )
                trace.mark("validate", ok=False, error=str(exc), attempt=attempt)
            except Exception as exc:
                last_exc = exc
                logger.error(
                    "Notes generation failed topic=%s attempt=%s: %s",
                    topic,
                    attempt,
                    exc,
                )
                trace.mark("generate_error", attempt=attempt, error=str(exc)[:200])

        raise RuntimeError(f"Exam notes pipeline failed for '{topic}': {last_exc}") from last_exc


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
    max_retries: int = 2,
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
