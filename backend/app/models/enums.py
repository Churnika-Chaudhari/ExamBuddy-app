from enum import StrEnum


class DocumentCategory(StrEnum):
    PYQ = "pyq"
    NOTES = "notes"
    STUDY_MATERIAL = "study_material"
    OTHER = "other"


class FileType(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    IMAGE = "image"


class ProcessingStatus(StrEnum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class AnalysisStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class NoteType(StrEnum):
    GENERATED = "generated"
    SIMPLIFIED = "simplified"
    MANUAL = "manual"


class NoteSourceType(StrEnum):
    ANALYSIS = "analysis"
    DOCUMENT = "document"
    TOPICS = "topics"


class QuizType(StrEnum):
    MCQ = "mcq"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    FILL_BLANK = "fill_blank"
    MIXED = "mixed"


class QuizDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class AIProvider(StrEnum):
    OPENAI = "openai"
    GEMINI = "gemini"
