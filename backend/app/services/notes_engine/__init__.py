"""ExamBuddy Notes Engine — exam-oriented notes generation pipeline."""

from app.services.notes_engine.pipeline import ExamNotesPipeline, generate_exam_notes_result
from app.services.notes_engine.schema import (
    EXAM_NOTE_FIELDS,
    GEMINI_EXAM_NOTES_RESPONSE_SCHEMA,
    PROMPT_VERSION,
)
from app.services.notes_engine.validator import NotesSchemaError, NotesValidationError

__all__ = [
    "ExamNotesPipeline",
    "EXAM_NOTE_FIELDS",
    "GEMINI_EXAM_NOTES_RESPONSE_SCHEMA",
    "PROMPT_VERSION",
    "NotesSchemaError",
    "NotesValidationError",
    "generate_exam_notes_result",
]
