"""
Stage 3 — Textbook-quality exam notes generation (v30 sectioned engine).

Purpose:
  Produce a complete, NotebookLM-quality university engineering exam-notes
  chapter for ONE normalized topic, covering every required heading
  (Definition, Core Concept, Working Principle, Architecture, Flow Diagram,
  Formula, Algorithm, Example, Advantages/Disadvantages, Applications,
  Comparison, PYQ Perspective, 2/5/10-Mark Answers, Viva, Interview, Common
  Mistakes, Memory Tricks, Revision Notes, Keywords, Summary).

Inputs (only):
  - Subject
  - Topic (Stage 2 textbook name)
  - Exam Priority (High / Medium / Low / Standard)

Architecture:
  A full chapter is NEVER produced in one call. SectionedNotesPipeline issues
  ~11 focused Gemini calls (batches), each with its own compact responseSchema,
  merges the results, and renders ONE long-form markdown document
  (~2500-5000 words).

Outputs:
  - Markdown notes + structured JSON (all section fields, for storage/API)

Isolation rules:
  - Never receives PYQ text, RAG, analysis snippets, or question wording.
  - Never invents actual PYQs — only question PATTERNS.
  - UNKNOWN_TOPIC when the topic is too ambiguous to teach accurately.

Failure modes:
  - Any batch invalid after its one repair attempt -> NotesSchemaError
    (structured backend error) — NO local template / fake notes fallback.
  - UNKNOWN_TOPIC -> NotesValidationError
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from app.core.exceptions import ExternalServiceError
from app.services.ai.notes_sanitizer import is_placeholder_notes
from app.services.notes_engine.pipeline import SectionedNotesPipeline
from app.services.notes_engine.prompt_builder import normalize_exam_priority
from app.services.notes_engine.schema import SECTIONED_ENGINE_ID, SECTIONED_PROMPT_VERSION
from app.services.notes_engine.validator import NotesSchemaError
from app.services.pipeline.three_stage.models import PIPELINE_VERSION

logger = logging.getLogger("exambuddy.pipeline.stage3")

# (system_prompt, user_prompt, response_schema, max_output_tokens, temperature)
GenerateSectionJsonFn = Callable[
    [str, str, dict[str, Any], int, float], Awaitable[tuple[dict[str, Any], dict[str, Any]]]
]


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
    generate_section_json: GenerateSectionJsonFn,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Run Stage 3 sectioned notes generation.

    Returns (result, metadata) where result has notes/summary/structured/word_count.
    """
    pipeline = SectionedNotesPipeline()
    result, metadata = await pipeline.run(
        topic=topic,
        subject=subject,
        exam_priority=exam_priority,
        generate_section_json=generate_section_json,
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
            "prompt_version": SECTIONED_PROMPT_VERSION,
            "notes_engine": SECTIONED_ENGINE_ID,
            "notes_input": "subject_topic_exam_priority_only",
            "generation_mode": "ai_sectioned",
            "structured_json_mode": True,
        }
    )
    if result.get("structured"):
        metadata["structured_notes"] = result["structured"]
    return result, metadata


def stage3_generate_json_factory(llm_service) -> GenerateSectionJsonFn:
    """Build the per-section Gemini structured-JSON callback used by Stage 3.

    Each section batch supplies its own responseSchema / max_output_tokens /
    temperature — small and focused, never one mega-call.
    """

    async def _generate_section_json(
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        max_output_tokens: int,
        temperature: float,
    ):
        return await llm_service.generate_notes_section_json(
            system_prompt,
            user_prompt,
            response_schema=response_schema,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            top_p=0.9,
        )

    return _generate_section_json


__all__ = [
    "build_stage3_notes_inputs",
    "run_stage3_notes",
    "stage3_generate_json_factory",
    "GenerateSectionJsonFn",
]
