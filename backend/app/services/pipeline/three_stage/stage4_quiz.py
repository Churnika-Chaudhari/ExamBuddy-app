"""
Stage 4 — Quiz generation from analysis context and optional study notes.

Purpose:
  Generate exam-style quiz questions for a subject using normalized topics.

Inputs:
  - Subject (required)
  - Topic list (from Stage 2 analysis)
  - Bounded context: analysis summaries, PYQ excerpts, generated notes (optional)

Outputs:
  - JSON: { title, questions[] } compatible with QuizResponse mapping

Isolation rules:
  - Stage 4 may assemble bounded PYQ/notes context internally.
  - Stage 3 notes prompts never receive this context.

Failure modes:
  - Provider failure → local template quiz (caller decides persistence)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.services.pipeline.three_stage.models import PIPELINE_VERSION

logger = logging.getLogger("exambuddy.pipeline.stage4")

GenerateJsonFn = Callable[[str, str], Awaitable[tuple[dict[str, Any], dict[str, Any]]]]

# Token budgets for Stage 4 context assembly (internal only).
MAX_QUIZ_CONTENT_CHARS = 30_000
MAX_ANALYSIS_SUMMARY_CHARS = 3_000
MAX_DOCUMENT_EXCERPT_CHARS = 6_000
MAX_NOTES_EXCERPT_CHARS = 4_000

QUIZ_GENERATE_SYSTEM_PROMPT = """You generate exam quizzes for students from PYQ analysis and study notes.

Return JSON:
{
  "title": "Subject — Quiz Title",
  "questions": [
    {
      "id": "uuid-string",
      "question_text": "...",
      "question_type": "mcq|true_false|short_answer|fill_blank",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "B",
      "explanation": "...",
      "topic": "syllabus topic name"
    }
  ]
}

Rules:
- Questions must test real syllabus concepts from the provided content — not generic placeholders.
- For true_false: options = ["True", "False"]
- For fill_blank: use _____ in question_text, options = []
- For short_answer: options = []
- For mcq: exactly 4 plausible options with one clearly correct answer
- Match difficulty to level requested (easy = definitions, hard = application/tricky distinctions)
- Every question MUST tag the source topic from the provided topic list
- Use only the provided topics
- Write clear, unambiguous question text suitable for university exams
- Explanations must teach why the answer is correct in 1-3 sentences"""

QUIZ_GENERATE_USER_PROMPT = """Generate {num_questions} {quiz_type} questions at {difficulty} difficulty for this subject.

Subject: {subject}
Topics (use ONLY these): {topics}

Content from PYQ analysis and study notes:
{content}

Title the quiz "{subject} — {difficulty} Quiz". Each question must reference a specific topic and test exam-relevant understanding."""


@dataclass
class Stage4QuizInputs:
    """Bounded inputs for Stage 4 quiz generation."""

    subject: str
    topics: list[str]
    content: str = ""
    num_questions: int = 10
    quiz_type: str = "mcq"
    difficulty: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "topics": self.topics,
            "content_chars": len(self.content),
            "num_questions": self.num_questions,
            "quiz_type": self.quiz_type,
            "difficulty": self.difficulty,
        }


def build_stage4_quiz_inputs(
    *,
    subject: str,
    topics: list[str],
    content: str = "",
    num_questions: int = 10,
    quiz_type: str = "mcq",
    difficulty: str = "medium",
) -> Stage4QuizInputs:
    """Build canonical Stage 4 inputs with bounded content."""
    clipped = (content or "")[:MAX_QUIZ_CONTENT_CHARS]
    clean_topics = [t.strip() for t in topics if t and t.strip()][:25]
    return Stage4QuizInputs(
        subject=(subject or "General").strip() or "General",
        topics=clean_topics,
        content=clipped,
        num_questions=max(1, min(int(num_questions), 50)),
        quiz_type=quiz_type,
        difficulty=difficulty,
    )


def build_stage4_quiz_prompts(inputs: Stage4QuizInputs) -> tuple[str, str]:
    """Return (system, user) prompts for Stage 4."""
    user = QUIZ_GENERATE_USER_PROMPT.format(
        num_questions=inputs.num_questions,
        quiz_type=inputs.quiz_type,
        difficulty=inputs.difficulty,
        subject=inputs.subject,
        topics=", ".join(inputs.topics) if inputs.topics else "General",
        content=inputs.content or "No additional content.",
    )
    return QUIZ_GENERATE_SYSTEM_PROMPT, user


async def run_stage4_quiz(
    *,
    inputs: Stage4QuizInputs,
    generate_json: GenerateJsonFn,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run Stage 4 quiz generation. Returns quiz JSON + metadata."""
    system_prompt, user_prompt = build_stage4_quiz_prompts(inputs)
    result, metadata = await generate_json(system_prompt, user_prompt)
    metadata = dict(metadata or {})
    metadata.update(
        {
            "pipeline_version": PIPELINE_VERSION,
            "pipeline_stage": 4,
            "difficulty": inputs.difficulty,
            "quiz_type": inputs.quiz_type,
            "topics_count": len(inputs.topics),
        }
    )
    return result, metadata


__all__ = [
    "Stage4QuizInputs",
    "QUIZ_GENERATE_SYSTEM_PROMPT",
    "QUIZ_GENERATE_USER_PROMPT",
    "build_stage4_quiz_inputs",
    "build_stage4_quiz_prompts",
    "run_stage4_quiz",
    "GenerateJsonFn",
    "MAX_QUIZ_CONTENT_CHARS",
]
