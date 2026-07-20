"""Professor Alex lecture-notes schema (v18)."""

from __future__ import annotations

PROMPT_VERSION = "v18.0"

EXAM_NOTE_FIELDS = (
    "topic",
    "whatIsIt",
    "whyNeeded",
    "realLifeAnalogy",
    "coreConcept",
    "howItWorks",
    "architecture",
    "components",
    "diagram",
    "realWorldExample",
    "deepDive",
    "advantages",
    "disadvantages",
    "comparison",
    "commonMistakes",
    "vivaQuestions",
    "examQuestions",
    "mcqs",
    "memoryTricks",
    "revisionSheet",
    "keyTakeaways",
)

# Legacy + alias mapping into canonical v18 fields.
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "whatIsIt": ("whatIsIt", "definition", "introduction"),
    "whyNeeded": ("whyNeeded", "whyItMatters", "whyUsed", "why_used"),
    "realLifeAnalogy": ("realLifeAnalogy", "analogy"),
    "coreConcept": ("coreConcept", "keyConcepts", "key_concepts"),
    "howItWorks": ("howItWorks", "working", "workingPrinciple", "stepByStep", "flow"),
    "architecture": ("architecture",),
    "components": ("components", "types", "features"),
    "diagram": ("diagram",),
    "realWorldExample": ("realWorldExample", "examples", "example", "real_world_example"),
    "deepDive": ("deepDive", "detailedExplanation", "detailed_explanation"),
    "advantages": ("advantages",),
    "disadvantages": ("disadvantages",),
    "comparison": ("comparison", "table"),
    "commonMistakes": ("commonMistakes", "common_mistakes"),
    "vivaQuestions": ("vivaQuestions", "viva_questions", "interviewQuestions"),
    "examQuestions": (
        "examQuestions",
        "frequentlyAskedQuestions",
        "exam_questions",
        "universityQuestions",
    ),
    "mcqs": ("mcqs", "multipleChoice"),
    "memoryTricks": ("memoryTricks", "memoryTrick", "memory_trick", "mnemonic"),
    "revisionSheet": (
        "revisionSheet",
        "thirtySecondRevision",
        "thirty_second_revision",
        "summary",
    ),
    "keyTakeaways": (
        "keyTakeaways",
        "importantExamPoints",
        "important_exam_points",
        "keyPoints",
        "examTips",
    ),
}
