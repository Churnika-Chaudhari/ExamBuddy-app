"""
Four-stage ExamBuddy education pipeline — analysis orchestrator (Stages 1–2).

Purpose:
  Run topic extraction and normalization for PYQ analysis API.

Inputs:
  - Raw PYQ text + subject hint + document count

Outputs:
  - Analysis payload compatible with existing PYQAnalysisResponse fields
  - stage1_topics / stage2_topics for downstream Stage 3 notes and Stage 4 quiz

Isolation rules:
  - Stage 3 (notes) and Stage 4 (quiz) are separate API paths.
  - This orchestrator never generates study notes.

Failure modes:
  - Empty PYQ text → ValidationAppError
  - Stage 2 may mark topics as UNKNOWN_TOPIC (filtered from tables)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.services.notes_engine.schema import PROMPT_VERSION
from app.services.pipeline.three_stage.models import (
    PIPELINE_VERSION,
    Stage1Result,
    Stage2Result,
    TopicItem,
)
from app.services.pipeline.three_stage.stage1_extract import run_stage1
from app.services.pipeline.three_stage.stage2_normalize import run_stage2
from app.services.pipeline.topic_pipeline import ExtractedTopic, topics_to_analysis_payload

logger = logging.getLogger("exambuddy.pipeline.orchestrator")

GenerateJsonFn = Callable[[str, str], Awaitable[tuple[dict[str, Any], dict[str, Any]]]]


@dataclass
class TopicPipelineResult:
    stage1: Stage1Result
    stage2: Stage2Result
    analysis_payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


def stage2_to_analysis_payload(
    stage2: Stage2Result,
    *,
    num_documents: int = 1,
    num_questions: int = 0,
) -> dict[str, Any]:
    """Convert Stage 2 topics into the existing analysis API shape."""
    records = [
        ExtractedTopic(
            topic=item.name,
            canonical=item.name,
            frequency=item.frequency,
            frequently_asked=item.frequency >= 3,
            unit="General",
        )
        for item in stage2.topics
    ]
    if not records:
        return {
            "topic_frequency_table": [],
            "topic_table": [],
            "topic_frequency": {},
            "important_topics": [],
            "syllabus_topics": [],
            "repeated_questions": [],
            "exam_patterns": [],
            "summary": "No topics extracted from uploaded PYQs.",
            "stage1_topics": {"subject": stage2.subject, "topics": []},
            "stage2_topics": stage2.as_dict(),
        }

    payload = topics_to_analysis_payload(
        records,
        num_documents=num_documents,
        num_questions=num_questions or sum(r.frequency for r in records),
    )
    payload["subject"] = stage2.subject
    payload["stage1_topics"] = {
        "subject": stage2.subject,
        "topics": [{"name": t.name, "frequency": t.frequency} for t in stage2.topics],
    }
    payload["stage2_topics"] = stage2.as_dict()
    payload["summary"] = (
        f"Extracted and normalized {len(stage2.topics)} topics "
        f"for {stage2.subject} across {num_documents} paper(s)."
    )
    return payload


async def run_topic_pipeline(
    pyq_text: str,
    *,
    subject: str | None = None,
    num_documents: int = 1,
    generate_json: GenerateJsonFn | None = None,
) -> TopicPipelineResult:
    """
    Run Stage 1 + Stage 2 for PYQ analysis.

    Stage 3 (notes) and Stage 4 (quiz) are intentionally separate API paths.
    """
    stage1 = await run_stage1(
        pyq_text,
        subject=subject,
        num_documents=num_documents,
        generate_json=generate_json,
    )
    stage2 = await run_stage2(stage1, generate_json=generate_json)
    payload = stage2_to_analysis_payload(
        stage2,
        num_documents=num_documents,
        num_questions=int(stage1.metadata.get("questions_parsed") or 0),
    )
    metadata = {
        "pipeline": PIPELINE_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "notes_prompt_version": PROMPT_VERSION,
        "stage1": stage1.metadata,
        "stage2": stage2.metadata,
        "topics_extracted": len(stage2.topics),
        "subject": stage2.subject,
    }
    logger.info(
        "Topic pipeline complete subject=%s topics=%d pipeline=%s",
        stage2.subject,
        len(stage2.topics),
        PIPELINE_VERSION,
    )
    return TopicPipelineResult(
        stage1=stage1,
        stage2=stage2,
        analysis_payload=payload,
        metadata=metadata,
    )


__all__ = [
    "TopicItem",
    "Stage1Result",
    "Stage2Result",
    "TopicPipelineResult",
    "run_topic_pipeline",
    "stage2_to_analysis_payload",
    "PIPELINE_VERSION",
]
