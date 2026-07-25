"""
ExamBuddy four-stage education pipeline.

Stage 1 — Extract topics from PYQs (JSON only, no notes)
Stage 2 — Normalize to standard engineering textbook names
Stage 3 — Generate exam notes (Subject / Topic / Exam Priority only)
Stage 4 — Generate quizzes from analysis + optional notes context

Public API routes are unchanged; stages are composed by services.
"""

from app.services.pipeline.three_stage.models import (
    PIPELINE_VERSION,
    Stage1Result,
    Stage2Result,
    TopicItem,
)
from app.services.pipeline.three_stage.orchestrator import (
    TopicPipelineResult,
    run_topic_pipeline,
    stage2_to_analysis_payload,
)
from app.services.pipeline.three_stage.stage1_extract import run_stage1
from app.services.pipeline.three_stage.stage2_normalize import (
    UNKNOWN_TOPIC,
    lookup_stage2_topic,
    normalize_single_topic,
    normalize_topic_name_local,
    run_stage2,
)
from app.services.pipeline.three_stage.stage3_notes import (
    build_stage3_notes_inputs,
    run_stage3_notes,
    stage3_generate_json_factory,
)
from app.services.pipeline.three_stage.stage4_quiz import (
    QUIZ_GENERATE_SYSTEM_PROMPT,
    QUIZ_GENERATE_USER_PROMPT,
    Stage4QuizInputs,
    build_stage4_quiz_inputs,
    run_stage4_quiz,
)

__all__ = [
    "PIPELINE_VERSION",
    "TopicItem",
    "Stage1Result",
    "Stage2Result",
    "TopicPipelineResult",
    "Stage4QuizInputs",
    "run_topic_pipeline",
    "stage2_to_analysis_payload",
    "run_stage1",
    "run_stage2",
    "normalize_single_topic",
    "normalize_topic_name_local",
    "lookup_stage2_topic",
    "build_stage3_notes_inputs",
    "run_stage3_notes",
    "stage3_generate_json_factory",
    "build_stage4_quiz_inputs",
    "run_stage4_quiz",
    "QUIZ_GENERATE_SYSTEM_PROMPT",
    "QUIZ_GENERATE_USER_PROMPT",
    "UNKNOWN_TOPIC",
]
