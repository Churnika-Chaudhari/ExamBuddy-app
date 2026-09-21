"""
ExamBuddy Notes Engine — concise (v40) Stage-3 exam notes.

ONE focused Gemini call per topic produces a 300-600 word, seven-section
revision note: Definition, Working, Advantages, Disadvantages, Applications,
Example, Quick Revision. (Replaces the retired v30 "sectioned" engine, which
built a 2500-5000 word chapter from 11 paced calls.)
"""

from app.services.notes_engine.markdown_formatter import (
    normalize_concise_payload,
    render_concise_markdown,
)
from app.services.notes_engine.pipeline import (
    ConciseNotesPipeline,
    generate_concise_notes_result,
)
from app.services.notes_engine.schema import (
    CONCISE_ENGINE_ID,
    CONCISE_NOTES_RESPONSE_SCHEMA,
    CONCISE_PROMPT_VERSION,
    PROMPT_VERSION,
    SECTION_HEADINGS,
    SECTION_ORDER,
)
from app.services.notes_engine.validator import (
    NotesSchemaError,
    NotesValidationError,
    validate_concise_payload,
    validate_final_notes,
)

__all__ = [
    "ConciseNotesPipeline",
    "generate_concise_notes_result",
    "normalize_concise_payload",
    "render_concise_markdown",
    "validate_concise_payload",
    "validate_final_notes",
    "CONCISE_ENGINE_ID",
    "CONCISE_NOTES_RESPONSE_SCHEMA",
    "CONCISE_PROMPT_VERSION",
    "PROMPT_VERSION",
    "SECTION_HEADINGS",
    "SECTION_ORDER",
    "NotesSchemaError",
    "NotesValidationError",
]
