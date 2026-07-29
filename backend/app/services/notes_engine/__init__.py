"""ExamBuddy Notes Engine — sectioned (v30) exam-notes generation pipeline."""

from app.services.notes_engine.pipeline import (
    SectionedNotesPipeline,
    generate_sectioned_notes_result,
)
from app.services.notes_engine.schema import (
    PROMPT_VERSION,
    SECTION_ORDER,
    SECTION_SCHEMAS,
    SECTION_TITLES,
    SECTIONED_ENGINE_ID,
    SECTIONED_PROMPT_VERSION,
)
from app.services.notes_engine.validator import NotesSchemaError, NotesValidationError

__all__ = [
    "SectionedNotesPipeline",
    "generate_sectioned_notes_result",
    "PROMPT_VERSION",
    "SECTIONED_ENGINE_ID",
    "SECTIONED_PROMPT_VERSION",
    "SECTION_ORDER",
    "SECTION_SCHEMAS",
    "SECTION_TITLES",
    "NotesSchemaError",
    "NotesValidationError",
]
