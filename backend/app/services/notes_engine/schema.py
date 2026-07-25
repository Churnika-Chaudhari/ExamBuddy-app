"""ExamBuddy exam-oriented notes schema (v20)."""

from __future__ import annotations

from typing import Any

PROMPT_VERSION = "v21.0"

EXAM_NOTE_FIELDS = (
    "topic",
    "topicType",
    "definition",
    "introduction",
    "working",
    "architecture",
    "algorithm",
    "formula",
    "diagram",
    "flowchart",
    "pseudocode",
    "syntax",
    "codeExample",
    "sqlExample",
    "example",
    "timeComplexity",
    "spaceComplexity",
    "advantages",
    "disadvantages",
    "applications",
    "comparison",
    "frequentlyAskedQuestions",
    "twoMarkAnswer",
    "fiveMarkAnswer",
    "tenMarkAnswer",
    "revisionSummary",
    # Legacy aliases still accepted via FIELD_ALIASES
    "detailedExplanation",
    "keyConcepts",
    "formulae",
    "output",
    "vivaQuestions",
    "interviewQuestions",
    "commonMistakes",
    "keywords",
    "characteristics",
)

# Map aliases (including older prompt versions) into canonical fields.
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "topicType": ("topicType", "category", "type"),
    "definition": ("definition", "whatIsIt"),
    "introduction": ("introduction", "whyNeeded", "whyItMatters", "whyUsed"),
    "working": ("working", "howItWorks", "workingPrinciple", "stepByStep", "flow", "detailedExplanation"),
    "architecture": ("architecture",),
    "algorithm": ("algorithm",),
    "formula": ("formula", "formulae", "formulas", "importantFormulae"),
    "diagram": ("diagram",),
    "flowchart": ("flowchart", "flowChart"),
    "pseudocode": ("pseudocode", "pseudoCode"),
    "syntax": ("syntax",),
    "codeExample": ("codeExample", "code", "code_example"),
    "sqlExample": ("sqlExample", "sql", "sql_example"),
    "example": ("example", "examples", "realWorldExample", "real_world_example"),
    "timeComplexity": ("timeComplexity", "time_complexity"),
    "spaceComplexity": ("spaceComplexity", "space_complexity"),
    "advantages": ("advantages",),
    "disadvantages": ("disadvantages",),
    "applications": ("applications",),
    "comparison": ("comparison", "table"),
    "frequentlyAskedQuestions": (
        "frequentlyAskedQuestions",
        "examQuestions",
        "universityQuestions",
    ),
    "twoMarkAnswer": ("twoMarkAnswer", "two_mark_answer", "answer2Mark"),
    "fiveMarkAnswer": ("fiveMarkAnswer", "five_mark_answer", "answer5Mark"),
    "tenMarkAnswer": ("tenMarkAnswer", "ten_mark_answer", "answer10Mark"),
    "revisionSummary": (
        "revisionSummary",
        "revisionSheet",
        "thirtySecondRevision",
        "summary",
        "keyTakeaways",
    ),
    "output": ("output",),
    "vivaQuestions": ("vivaQuestions", "viva_questions"),
    "interviewQuestions": ("interviewQuestions", "interview_questions"),
    "commonMistakes": ("commonMistakes", "common_mistakes"),
    "keywords": ("keywords", "keyPoints"),
    "characteristics": ("characteristics",),
    "keyConcepts": ("keyConcepts", "components", "features"),
    "detailedExplanation": ("detailedExplanation", "deepDive", "coreConcept"),
    "formulae": ("formulae", "formulas", "importantFormulae", "formula"),
}

_STRING = {"type": "STRING"}
_STRING_ARRAY = {"type": "ARRAY", "items": {"type": "STRING"}}
_QA_ITEM = {
    "type": "OBJECT",
    "properties": {
        "question": _STRING,
        "answer": _STRING,
    },
}
_COMPARISON = {
    "type": "OBJECT",
    "properties": {
        "title": _STRING,
        "headers": _STRING_ARRAY,
        "rows": {"type": "ARRAY", "items": _STRING_ARRAY},
    },
}

# Gemini REST/SDK responseSchema (OpenAPI Schema subset). All content fields
# optional so the model can omit irrelevant sections or return UNKNOWN_TOPIC.
GEMINI_EXAM_NOTES_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "status": _STRING,
        "topic": _STRING,
        "topicType": _STRING,
        "definition": _STRING,
        "introduction": _STRING,
        "working": _STRING,
        "architecture": _STRING,
        "algorithm": _STRING,
        "formula": _STRING,
        "diagram": _STRING,
        "flowchart": _STRING,
        "pseudocode": _STRING,
        "syntax": _STRING,
        "codeExample": _STRING,
        "sqlExample": _STRING,
        "example": _STRING,
        "timeComplexity": _STRING,
        "spaceComplexity": _STRING,
        "advantages": _STRING_ARRAY,
        "disadvantages": _STRING_ARRAY,
        "applications": _STRING_ARRAY,
        "comparison": _COMPARISON,
        "frequentlyAskedQuestions": {"type": "ARRAY", "items": _QA_ITEM},
        "twoMarkAnswer": _STRING,
        "fiveMarkAnswer": _STRING,
        "tenMarkAnswer": _STRING,
        "revisionSummary": _STRING_ARRAY,
        "output": _STRING,
        "notes": _STRING,
        "summary": _STRING,
    },
}

# Canonical content fields used for structural presence checks.
SCHEMA_CONTENT_FIELDS = (
    "definition",
    "introduction",
    "working",
    "architecture",
    "algorithm",
    "formula",
    "diagram",
    "flowchart",
    "pseudocode",
    "syntax",
    "codeExample",
    "sqlExample",
    "example",
    "timeComplexity",
    "spaceComplexity",
    "advantages",
    "disadvantages",
    "applications",
    "comparison",
    "frequentlyAskedQuestions",
    "twoMarkAnswer",
    "fiveMarkAnswer",
    "tenMarkAnswer",
    "revisionSummary",
    "notes",
)

SCHEMA_STRING_FIELDS = frozenset(
    {
        "status",
        "topic",
        "topicType",
        "definition",
        "introduction",
        "working",
        "architecture",
        "algorithm",
        "formula",
        "diagram",
        "flowchart",
        "pseudocode",
        "syntax",
        "codeExample",
        "sqlExample",
        "example",
        "timeComplexity",
        "spaceComplexity",
        "twoMarkAnswer",
        "fiveMarkAnswer",
        "tenMarkAnswer",
        "output",
        "notes",
        "summary",
    }
)

SCHEMA_STRING_LIST_FIELDS = frozenset(
    {
        "advantages",
        "disadvantages",
        "applications",
        "revisionSummary",
        "keyConcepts",
        "keywords",
        "characteristics",
        "commonMistakes",
        "formulae",
    }
)

SCHEMA_QA_LIST_FIELDS = frozenset(
    {
        "frequentlyAskedQuestions",
        "vivaQuestions",
        "interviewQuestions",
        "examQuestions",
    }
)
