"""Exam-oriented structured notes schema (v17)."""

from __future__ import annotations

PROMPT_VERSION = "v17.0"

# Canonical JSON fields returned by the exam-notes LLM call.
EXAM_NOTE_FIELDS = (
    "topic",
    "definition",
    "whyItMatters",
    "keyConcepts",
    "detailedExplanation",
    "diagram",
    "table",
    "examples",
    "memoryTrick",
    "importantExamPoints",
    "commonMistakes",
    "frequentlyAskedQuestions",
    "vivaQuestions",
    "thirtySecondRevision",
    "summary",
)

# Accept legacy / alias keys from older generations.
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "whyItMatters": ("whyItMatters", "whyUsed", "why_used", "whyNeeded", "why_needed"),
    "keyConcepts": ("keyConcepts", "key_concepts", "components", "types", "features"),
    "detailedExplanation": (
        "detailedExplanation",
        "detailed_explanation",
        "working",
        "workingPrinciple",
        "architecture",
    ),
    "examples": ("examples", "example", "realWorldExample", "real_world_example"),
    "memoryTrick": ("memoryTrick", "memory_trick", "mnemonic"),
    "importantExamPoints": (
        "importantExamPoints",
        "important_exam_points",
        "keyPoints",
        "key_points",
        "examTips",
    ),
    "commonMistakes": ("commonMistakes", "common_mistakes"),
    "frequentlyAskedQuestions": (
        "frequentlyAskedQuestions",
        "examQuestions",
        "exam_questions",
        "universityQuestions",
    ),
    "vivaQuestions": ("vivaQuestions", "viva_questions", "interviewQuestions"),
    "thirtySecondRevision": (
        "thirtySecondRevision",
        "thirty_second_revision",
        "revisionSheet",
        "summary",
    ),
    "table": ("table", "comparison"),
}
