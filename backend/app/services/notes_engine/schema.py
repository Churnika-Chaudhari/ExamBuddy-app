"""ExamBuddy exam-oriented notes schema (v20 legacy + v30 sectioned engine)."""

from __future__ import annotations

from typing import Any

# Bumped so notes_service treats EVERY previously cached note (short single-call
# v17-v21 JSON, any engine) as stale and regenerates through the new sectioned
# pipeline. See SECTIONED_ENGINE_ID / SECTIONED_PROMPT_VERSION below for the
# canonical identifiers of the current engine.
PROMPT_VERSION = "v30.0-sectioned"

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
#
# propertyOrdering matters more than it looks: Gemini 2.5 models generate
# fields in this exact order, and open-ended fields (working/introduction/
# example) can ramble far past a reasonable length and consume the entire
# maxOutputTokens budget, truncating the JSON before later fields are ever
# written (observed: "working" alone produced 100k+ chars for a single
# topic). Short, validation-critical fields (definition, mark-wise answers,
# revisionSummary) are ordered FIRST so they always land safely in the
# output even if a later free-form field gets cut off by the token cap.
GEMINI_EXAM_NOTES_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "status": _STRING,
        "topic": _STRING,
        "topicType": _STRING,
        "definition": _STRING,
        "twoMarkAnswer": _STRING,
        "fiveMarkAnswer": _STRING,
        "tenMarkAnswer": _STRING,
        "revisionSummary": _STRING_ARRAY,
        "advantages": _STRING_ARRAY,
        "disadvantages": _STRING_ARRAY,
        "applications": _STRING_ARRAY,
        "frequentlyAskedQuestions": {"type": "ARRAY", "items": _QA_ITEM},
        "comparison": _COMPARISON,
        "timeComplexity": _STRING,
        "spaceComplexity": _STRING,
        "formula": _STRING,
        "syntax": _STRING,
        "codeExample": _STRING,
        "sqlExample": _STRING,
        "algorithm": _STRING,
        "architecture": _STRING,
        "diagram": _STRING,
        "flowchart": _STRING,
        "pseudocode": _STRING,
        "introduction": _STRING,
        "example": _STRING,
        "working": _STRING,
        "output": _STRING,
        "notes": _STRING,
        "summary": _STRING,
    },
    "propertyOrdering": [
        "status",
        "topic",
        "topicType",
        "definition",
        "twoMarkAnswer",
        "fiveMarkAnswer",
        "tenMarkAnswer",
        "revisionSummary",
        "advantages",
        "disadvantages",
        "applications",
        "frequentlyAskedQuestions",
        "comparison",
        "timeComplexity",
        "spaceComplexity",
        "formula",
        "syntax",
        "codeExample",
        "sqlExample",
        "algorithm",
        "architecture",
        "diagram",
        "flowchart",
        "pseudocode",
        "introduction",
        "example",
        "working",
        "output",
        "notes",
        "summary",
    ],
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


# =============================================================================
# v30 — Sectioned NotebookLM-style notes engine.
#
# Replaces the single mega-call schema above for Stage-3 topic notes. Instead
# of one huge JSON blob (prone to truncation / short rambling fields), a full
# textbook-chapter document is assembled from ~11 small, focused Gemini calls
# ("batches" — see SECTION_ORDER). Each batch has its own compact responseSchema
# so it can never consume the whole token budget or crowd out other sections.
#
# Batches are merged into ONE structured dict, then rendered into a single
# long-form markdown chapter covering every required heading — "Not Applicable"
# when a heading has no accurate content for the topic, never omitted.
# =============================================================================

SECTIONED_ENGINE_ID = "exambuddy_sectioned_v30"
SECTIONED_PROMPT_VERSION = PROMPT_VERSION

# Word-count gates for the FINAL merged markdown document.
MIN_WORD_COUNT_SOFT = 2000
MIN_WORD_COUNT_TARGET = 2500
MAX_WORD_COUNT_SOFT = 5500  # small overrun tolerated — never hard-truncated

# Canonical required-heading keywords (case-insensitive substring match against
# the final rendered markdown). Every one of these MUST appear.
REQUIRED_HEADING_KEYWORDS: tuple[str, ...] = (
    "definition",
    "introduction",
    "core concept",
    "working principle",
    "architecture",
    "flow diagram",
    "mathematical formula",
    "algorithm",
    "example",
    "advantages",
    "disadvantages",
    "applications",
    "comparison",
    "pyq perspective",
    "2 marks answer",
    "5 marks answer",
    "10 marks answer",
    "viva questions",
    "interview questions",
    "common mistakes",
    "memory tricks",
    "revision notes",
    "keywords",
    "summary",
)

_SEC_STRING = {"type": "STRING"}
_SEC_STRING_ARRAY = {"type": "ARRAY", "items": _SEC_STRING}
_SEC_QA_ITEM = {
    "type": "OBJECT",
    "properties": {"question": _SEC_STRING, "answer": _SEC_STRING},
    "propertyOrdering": ["question", "answer"],
}
_SEC_QA_ARRAY = {"type": "ARRAY", "items": _SEC_QA_ITEM}
_SEC_TABLE_ROW_ITEM = {
    "type": "OBJECT",
    "properties": {"point": _SEC_STRING, "explanation": _SEC_STRING},
    "propertyOrdering": ["point", "explanation"],
}
_SEC_TABLE_ROW_ARRAY = {"type": "ARRAY", "items": _SEC_TABLE_ROW_ITEM}
_SEC_COMPARISON_TABLE = {
    "type": "OBJECT",
    "properties": {
        "title": _SEC_STRING,
        "headers": _SEC_STRING_ARRAY,
        "rows": {"type": "ARRAY", "items": _SEC_STRING_ARRAY},
    },
    "propertyOrdering": ["title", "headers", "rows"],
}
_SEC_COMPARISON_ARRAY = {"type": "ARRAY", "items": _SEC_COMPARISON_TABLE}

# Ordered batches — NEVER collapse into one mega-call. Order matters: batch 1
# seeds topic/definition context reused (as a short recap) by every later batch.
#
# Free-tier tradeoff note: 11 calls/topic paced at ~14s apart (see
# notes_engine.pipeline.SECTION_CALL_MIN_SPACING_SECONDS) takes ~2.5-3+ min
# per topic just for RPM pacing, before any 429 backoff. If a project's daily
# free-tier RPD (requests-per-day) is the binding constraint rather than RPM,
# merging adjacent batches (e.g. 11 -> 5-6, such as combining
# architecture_diagram+formula_algorithm, or viva+interview into one call)
# would cut total calls/topic roughly in half while keeping every structured
# field and required heading intact. This was intentionally NOT done here:
# the user wants a multi-call sectioned document (never one mega-call), and
# pacing/backoff alone is sufficient for the common RPM-exhaustion failure
# mode. Only reduce batch count if RPD, not RPM, turns out to be the actual
# blocker in production logs.
SECTION_ORDER: tuple[str, ...] = (
    "topic_definition_intro",
    "core_working",
    "architecture_diagram",
    "formula_algorithm",
    "example_adv_disadv",
    "applications_comparison",
    "pyq_marks",
    "viva",
    "interview",
    "mistakes_tricks",
    "revision_keywords_summary",
)

SECTION_TITLES: dict[str, str] = {
    "topic_definition_intro": "Topic + Definition + Introduction",
    "core_working": "Core Concept + Working Principle",
    "architecture_diagram": "Architecture/Components + Flow Diagram",
    "formula_algorithm": "Mathematical Formula + Algorithm",
    "example_adv_disadv": "Example + Advantages + Disadvantages",
    "applications_comparison": "Applications + Comparison",
    "pyq_marks": "PYQ Perspective + 2/5/10 Marks Answers",
    "viva": "Viva Questions (10 Q+A)",
    "interview": "Interview Questions (10 Q+A)",
    "mistakes_tricks": "Common Mistakes + Memory Tricks",
    "revision_keywords_summary": "Revision Notes + Keywords + Summary",
}

SECTION_SCHEMAS: dict[str, dict[str, Any]] = {
    "topic_definition_intro": {
        "type": "OBJECT",
        "properties": {
            "status": _SEC_STRING,
            "topic": _SEC_STRING,
            "definition_simple": _SEC_STRING,
            "definition_technical": _SEC_STRING,
            "definition_exam": _SEC_STRING,
            "introduction": _SEC_STRING,
        },
        "propertyOrdering": [
            "status",
            "topic",
            "definition_simple",
            "definition_technical",
            "definition_exam",
            "introduction",
        ],
    },
    "core_working": {
        "type": "OBJECT",
        "properties": {"core_concept": _SEC_STRING, "working_principle": _SEC_STRING},
        "propertyOrdering": ["core_concept", "working_principle"],
    },
    "architecture_diagram": {
        "type": "OBJECT",
        "properties": {"architecture": _SEC_STRING, "diagram": _SEC_STRING},
        "propertyOrdering": ["architecture", "diagram"],
    },
    "formula_algorithm": {
        "type": "OBJECT",
        "properties": {"formula": _SEC_STRING, "algorithm": _SEC_STRING},
        "propertyOrdering": ["formula", "algorithm"],
    },
    "example_adv_disadv": {
        "type": "OBJECT",
        "properties": {
            "examples": _SEC_STRING_ARRAY,
            "advantages": _SEC_TABLE_ROW_ARRAY,
            "disadvantages": _SEC_TABLE_ROW_ARRAY,
        },
        "propertyOrdering": ["examples", "advantages", "disadvantages"],
    },
    "applications_comparison": {
        "type": "OBJECT",
        "properties": {"applications": _SEC_STRING_ARRAY, "comparison": _SEC_COMPARISON_ARRAY},
        "propertyOrdering": ["applications", "comparison"],
    },
    "pyq_marks": {
        "type": "OBJECT",
        "properties": {
            "pyq_perspective": _SEC_STRING,
            "exam_answer_2m": _SEC_STRING,
            "exam_answer_5m": _SEC_STRING,
            "exam_answer_10m": _SEC_STRING,
        },
        "propertyOrdering": ["pyq_perspective", "exam_answer_2m", "exam_answer_5m", "exam_answer_10m"],
    },
    "viva": {
        "type": "OBJECT",
        "properties": {"viva": _SEC_QA_ARRAY},
        "propertyOrdering": ["viva"],
    },
    "interview": {
        "type": "OBJECT",
        "properties": {"interview": _SEC_QA_ARRAY},
        "propertyOrdering": ["interview"],
    },
    "mistakes_tricks": {
        "type": "OBJECT",
        "properties": {"common_mistakes": _SEC_STRING_ARRAY, "memory_tricks": _SEC_STRING_ARRAY},
        "propertyOrdering": ["common_mistakes", "memory_tricks"],
    },
    "revision_keywords_summary": {
        "type": "OBJECT",
        "properties": {
            "revision_points": _SEC_STRING_ARRAY,
            "keywords": _SEC_STRING_ARRAY,
            "summary": _SEC_STRING,
        },
        "propertyOrdering": ["revision_points", "keywords", "summary"],
    },
}

# Per-batch generation budget. Small and focused — the whole point of the
# sectioned design is that no single call can ever run away with the token
# budget the way the old mega-call did.
SECTION_MAX_OUTPUT_TOKENS: dict[str, int] = {
    "topic_definition_intro": 2048,
    "core_working": 2048,
    "architecture_diagram": 2048,
    "formula_algorithm": 2048,
    "example_adv_disadv": 2560,
    "applications_comparison": 2048,
    "pyq_marks": 2560,
    "viva": 3072,
    "interview": 3072,
    "mistakes_tricks": 1536,
    "revision_keywords_summary": 1536,
}

SECTION_TEMPERATURE: dict[str, float] = {
    "topic_definition_intro": 0.3,
    "core_working": 0.35,
    "architecture_diagram": 0.35,
    "formula_algorithm": 0.3,
    "example_adv_disadv": 0.4,
    "applications_comparison": 0.35,
    "pyq_marks": 0.35,
    "viva": 0.4,
    "interview": 0.4,
    "mistakes_tricks": 0.4,
    "revision_keywords_summary": 0.35,
}

# Minimum-content gates checked per batch BEFORE merging (see validator.py).
# "kind": text -> non-empty string ("Not Applicable" counts as valid content);
# "kind": list -> at least min_items entries; "kind": qa_list -> at least
# min_items {question, answer} pairs.
SECTION_VALIDATION_RULES: dict[str, dict[str, dict[str, Any]]] = {
    "topic_definition_intro": {
        "topic": {"kind": "text"},
        "definition_exam": {"kind": "text"},
        "introduction": {"kind": "text"},
    },
    "core_working": {
        "core_concept": {"kind": "text"},
        "working_principle": {"kind": "text"},
    },
    "architecture_diagram": {
        "architecture": {"kind": "text"},
        "diagram": {"kind": "text"},
    },
    "formula_algorithm": {
        "formula": {"kind": "text"},
        "algorithm": {"kind": "text"},
    },
    "example_adv_disadv": {
        "examples": {"kind": "list", "min_items": 1},
        "advantages": {"kind": "list", "min_items": 3},
        "disadvantages": {"kind": "list", "min_items": 2},
    },
    "applications_comparison": {
        "applications": {"kind": "list", "min_items": 3},
        "comparison": {"kind": "list", "min_items": 1},
    },
    "pyq_marks": {
        "pyq_perspective": {"kind": "text"},
        "exam_answer_2m": {"kind": "text"},
        "exam_answer_5m": {"kind": "text"},
        "exam_answer_10m": {"kind": "text"},
    },
    "viva": {"viva": {"kind": "qa_list", "min_items": 6}},
    "interview": {"interview": {"kind": "qa_list", "min_items": 6}},
    "mistakes_tricks": {
        "common_mistakes": {"kind": "list", "min_items": 3},
        "memory_tricks": {"kind": "list", "min_items": 2},
    },
    "revision_keywords_summary": {
        "revision_points": {"kind": "list", "min_items": 5},
        "keywords": {"kind": "list", "min_items": 5},
        "summary": {"kind": "text"},
    },
}
