"""
Stage 3 — Concise exam-notes generation (v40 concise engine).

Purpose:
  Produce short, exam-ready revision notes for ONE normalized topic with
  exactly seven sections: Definition, Working, Advantages, Disadvantages,
  Applications, Example, Quick Revision (target 300-600 words).

Inputs (only):
  - Subject
  - Topic (Stage 2 textbook name)

Architecture:
  ONE focused Gemini structured-JSON call, plus at most one scoped repair
  call when validation fails. (Replaces the v30 sectioned engine's 11 paced
  batch calls, which existed to build a long textbook chapter.)

Isolation rules:
  - Never receives PYQ text, RAG passages, or question wording — a PYQ only
    identifies which topic to write about.
  - Never mentions PYQs, marks, AI, or the generation process.
  - UNKNOWN_TOPIC when the topic is not a teachable engineering concept.

Failure modes:
  - Invalid after the repair attempt -> NotesSchemaError (structured error).
  - Empty / placeholder output -> ExternalServiceError.
  - No local template / fake-notes fallback, ever.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from app.core.exceptions import ExternalServiceError
from app.services.ai.notes_sanitizer import is_placeholder_notes
from app.services.notes_engine.pipeline import ConciseNotesPipeline
from app.services.notes_engine.prompt_builder import clean_topic, normalize_exam_priority
from app.services.notes_engine.schema import (
    CONCISE_ENGINE_ID,
    CONCISE_PROMPT_VERSION,
    NOTES_TOP_P,
)
from app.services.pipeline.three_stage.models import PIPELINE_VERSION

logger = logging.getLogger("exambuddy.pipeline.stage3")

# (system_prompt, user_prompt, response_schema, max_output_tokens, temperature)
GenerateNotesJsonFn = Callable[
    [str, str, dict[str, Any], int, float], Awaitable[tuple[dict[str, Any], dict[str, Any]]]
]


def build_stage3_notes_inputs(
    *,
    topic: str,
    subject: str | None = None,
    frequency: int | None = None,
    exam_priority: str = "",
) -> dict[str, Any]:
    """Canonical Stage 3 input bundle — no PYQ/RAG/pipeline text.

    Exam priority is still normalized for ordering/analytics upstream, but it
    is not sent to the model: concise notes have one fixed depth.
    """
    return {
        "topic": clean_topic(topic),
        "subject": (subject or "General").strip() or "General",
        "frequency": frequency,
        "exam_priority": normalize_exam_priority(exam_priority, frequency=frequency),
    }


async def run_stage3_notes(
    *,
    topic: str,
    subject: str | None = None,
    generate_notes_json: GenerateNotesJsonFn,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Run Stage 3 concise notes generation.

    Returns (result, metadata) where result has notes/summary/structured/word_count.
    """
    result, metadata = await ConciseNotesPipeline().run(
        topic=topic,
        subject=subject,
        generate_notes_json=generate_notes_json,
    )

    notes_text = (result.get("notes") or "").strip()
    if not notes_text:
        raise ExternalServiceError("AI returned empty notes content")
    if is_placeholder_notes(notes_text):
        raise ExternalServiceError("AI returned instruction placeholders instead of study notes")

    metadata = dict(metadata or {})
    metadata.update(
        {
            "pipeline_version": PIPELINE_VERSION,
            "pipeline_stage": 3,
            "prompt_version": CONCISE_PROMPT_VERSION,
            "notes_engine": CONCISE_ENGINE_ID,
            "notes_input": "subject_topic_only",
            "generation_mode": "ai_concise",
            "structured_json_mode": True,
        }
    )
    if result.get("structured"):
        metadata["structured_notes"] = result["structured"]
    return result, metadata


def stage3_generate_json_factory(llm_service) -> GenerateNotesJsonFn:
    """Build the structured-JSON callback Stage 3 hands to the notes pipeline."""

    async def _generate_notes_json(
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        max_output_tokens: int,
        temperature: float,
    ):
        return await llm_service.generate_structured_notes_json(
            system_prompt,
            user_prompt,
            response_schema=response_schema,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            top_p=NOTES_TOP_P,
        )

    return _generate_notes_json


__all__ = [
    "build_stage3_notes_inputs",
    "run_stage3_notes",
    "stage3_generate_json_factory",
    "GenerateNotesJsonFn",
]
