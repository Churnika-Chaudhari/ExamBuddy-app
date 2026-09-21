"""
ExamBuddy concise exam-notes schema (v40).

Product pivot: Stage 3 no longer produces a long NotebookLM-style textbook
chapter assembled from 11 sectioned Gemini batches. It now produces ONE short,
exam-revision note per topic with exactly seven sections:

    Definition, Working, Advantages, Disadvantages, Applications, Example,
    Quick Revision

Target length for the whole rendered document is 300-600 words, so a single
focused structured-JSON call is enough (a second call only ever happens as a
one-shot repair when validation fails).
"""

from __future__ import annotations

from typing import Any

# Bumped so notes_service treats every previously cached note (short v15-v21
# single-call notes AND the long v30 sectioned chapters) as stale and
# regenerates it through the concise pipeline.
PROMPT_VERSION = "v40.0-concise"

CONCISE_ENGINE_ID = "exambuddy_concise_v40"
CONCISE_PROMPT_VERSION = PROMPT_VERSION

# The seven sections, in render order: (structured field, markdown heading).
SECTION_ORDER: tuple[tuple[str, str], ...] = (
    ("definition", "1. Definition"),
    ("working", "2. Working"),
    ("advantages", "3. Advantages"),
    ("disadvantages", "4. Disadvantages"),
    ("applications", "5. Applications"),
    ("example", "6. Example"),
    ("quick_revision", "7. Quick Revision"),
)

SECTION_FIELDS: tuple[str, ...] = tuple(field for field, _ in SECTION_ORDER)
SECTION_HEADINGS: tuple[str, ...] = tuple(heading for _, heading in SECTION_ORDER)

# Accepted model spellings for each canonical field. Gemini follows the
# responseSchema closely, but Groq/OpenAI JSON mode is looser.
FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "topic": ("topic", "title", "name"),
    "definition": ("definition", "what_is_it", "whatIsIt"),
    "working": ("working", "steps", "working_steps", "workingSteps", "how_it_works", "howItWorks"),
    "advantages": ("advantages", "pros", "benefits"),
    "disadvantages": ("disadvantages", "cons", "limitations", "drawbacks"),
    "applications": ("applications", "real_world_applications", "realWorldApplications", "uses"),
    "example": ("example", "worked_example", "workedExample", "examples"),
    "quick_revision": (
        "quick_revision",
        "quickRevision",
        "revision",
        "revision_points",
        "revisionPoints",
        "last_minute_points",
    ),
}

TEXT_FIELDS = frozenset({"topic", "definition", "example"})
LIST_FIELDS = frozenset({"working", "advantages", "disadvantages", "applications", "quick_revision"})

_STRING = {"type": "STRING"}
_STRING_ARRAY = {"type": "ARRAY", "items": _STRING}
_APPLICATION_ITEM = {
    "type": "OBJECT",
    "properties": {"name": _STRING, "detail": _STRING},
    "propertyOrdering": ["name", "detail"],
}

# Gemini responseSchema (OpenAPI subset). Everything is short by design, so
# unlike the old mega-call schema there is no risk of one field eating the
# whole token budget. propertyOrdering still matches the render order so a
# truncated response degrades predictably (earlier sections survive).
CONCISE_NOTES_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "status": _STRING,
        "topic": _STRING,
        "definition": _STRING,
        "working": _STRING_ARRAY,
        "advantages": _STRING_ARRAY,
        "disadvantages": _STRING_ARRAY,
        "applications": {"type": "ARRAY", "items": _APPLICATION_ITEM},
        "example": _STRING,
        "quick_revision": _STRING_ARRAY,
    },
    "propertyOrdering": [
        "status",
        "topic",
        "definition",
        "working",
        "advantages",
        "disadvantages",
        "applications",
        "example",
        "quick_revision",
    ],
}

# Per-section item counts from the product spec. `min` is enforced by the
# validator; `max` is enforced by the normalizer (extra items are trimmed
# rather than sent back for repair).
SECTION_ITEM_LIMITS: dict[str, tuple[int, int]] = {
    "working": (4, 7),
    "advantages": (3, 5),
    "disadvantages": (2, 4),
    "applications": (3, 5),
    "quick_revision": (4, 6),
}

# Minimum characters for the free-text sections — rejects "N/A"-style stubs.
MIN_DEFINITION_CHARS = 80
MIN_EXAMPLE_CHARS = 60
MIN_LIST_ITEM_CHARS = 12

# Defensive caps so a rambling model can never turn concise notes long again.
MAX_TEXT_FIELD_CHARS = 900
MAX_LIST_ITEM_CHARS = 320

# Word-count gates for the FINAL rendered markdown. The prompt targets
# 300-600; the hard gate is a wider soft band so a slightly long or slightly
# terse-but-complete note is not thrown away.
TARGET_WORD_COUNT_MIN = 300
TARGET_WORD_COUNT_MAX = 600
MIN_WORD_COUNT_SOFT = 200
MAX_WORD_COUNT_SOFT = 800

# Single focused call — small budget is plenty for ~600 words of JSON.
NOTES_MAX_OUTPUT_TOKENS = 3072
NOTES_TEMPERATURE = 0.3
NOTES_TOP_P = 0.9
