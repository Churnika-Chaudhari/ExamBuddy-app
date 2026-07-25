"""
Stage 3 — Textbook-quality exam notes generation.

Purpose:
  Produce university engineering exam notes for ONE normalized topic.

Inputs (only):
  - Subject
  - Topic (Stage 2 textbook name)
  - Exam Priority (High / Medium / Low / Standard)

Outputs:
  - Markdown notes + optional structured JSON sections

Isolation rules:
  - Never receives PYQ text, RAG, analysis snippets, or question wording.
  - Accuracy over completeness; UNKNOWN_TOPIC when confidence is low.

Failure modes:
  - Schema invalid after one repair → NotesSchemaError (structured backend error)
  - UNKNOWN_TOPIC → NotesValidationError
  - Provider unavailable → local fallback (caller may surface error)
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from app.core.exceptions import ExternalServiceError
from app.services.ai.notes_sanitizer import is_placeholder_notes
from app.services.notes_engine.pipeline import ExamNotesPipeline
from app.services.notes_engine.prompt_builder import normalize_exam_priority
from app.services.notes_engine.schema import GEMINI_EXAM_NOTES_RESPONSE_SCHEMA, PROMPT_VERSION
from app.services.notes_engine.validator import NotesSchemaError
from app.services.pipeline.three_stage.models import PIPELINE_VERSION

logger = logging.getLogger("exambuddy.pipeline.stage3")

GenerateJsonFn = Callable[[str, str], Awaitable[tuple[dict[str, Any], dict[str, Any]]]]


def build_stage3_notes_inputs(
    *,
    topic: str,
    subject: str | None = None,
    frequency: int | None = None,
    exam_priority: str = "",
) -> dict[str, Any]:
    """Canonical Stage 3 input bundle — no PYQ/RAG/pipeline text."""
    priority = normalize_exam_priority(exam_priority, frequency=frequency)
    return {
        "topic": (topic or "").strip(),
        "subject": (subject or "General").strip() or "General",
        "frequency": frequency,
        "exam_priority": priority,
    }


async def run_stage3_notes(
    *,
    topic: str,
    subject: str | None = None,
    exam_priority: str = "",
    generate_json: GenerateJsonFn,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Run Stage 3 notes generation via the notes engine.

    Returns (result, metadata) where result has notes/summary/structured.
    """
    pipeline = ExamNotesPipeline(max_retries=1)
    result, metadata = await pipeline.run(
        topic=topic,
        generate_json=generate_json,
        subject=subject,
        exam_priority=exam_priority,
    )

    notes_text = (result.get("notes") or "").strip()
    if not notes_text:
        raise ExternalServiceError("AI returned empty notes content")
    if is_placeholder_notes(notes_text):
        raise ExternalServiceError(
            "AI returned instruction placeholders instead of study notes"
        )

    metadata = dict(metadata or {})
    metadata.update(
        {
            "pipeline_version": PIPELINE_VERSION,
            "pipeline_stage": 3,
            "prompt_version": PROMPT_VERSION,
            "notes_input": "subject_topic_exam_priority_only",
            "generation_mode": "ai_only",
            "structured_json_mode": True,
        }
    )
    if result.get("structured"):
        metadata["structured_notes"] = result["structured"]
    return result, metadata


def stage3_generate_json_factory(llm_service) -> GenerateJsonFn:
    """Build the Gemini structured-JSON callback used by Stage 3."""
    from app.services.ai.base_provider import GEMINI_MAX_NOTES_TOKENS

    async def _generate_json(system_prompt: str, user_prompt: str):
        return await llm_service._generate_json(
            system_prompt,
            user_prompt,
            max_output_tokens=GEMINI_MAX_NOTES_TOKENS,
            temperature=0.3,
            top_p=0.9,
            response_schema=GEMINI_EXAM_NOTES_RESPONSE_SCHEMA,
        )

    return _generate_json


__all__ = [
    "build_stage3_notes_inputs",
    "run_stage3_notes",
    "stage3_generate_json_factory",
    "GenerateJsonFn",
]
