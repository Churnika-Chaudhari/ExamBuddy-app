from datetime import datetime

from pydantic import Field

from app.models.enums import QuizDifficulty, QuizType
from app.schemas.common import BaseSchema


class QuizQuestion(BaseSchema):
    id: str
    question_text: str
    question_type: QuizType
    options: list[str] = []
    correct_answer: str
    explanation: str | None = None
    topic: str | None = None


class QuizGenerateRequest(BaseSchema):
    subject: str = Field(..., min_length=1, max_length=120)
    notes_id: str | None = None
    analysis_id: str | None = None
    topics: list[str] = Field(default_factory=list, max_length=30)
    title: str | None = Field(default=None, max_length=200)
    quiz_type: QuizType = QuizType.MIXED
    difficulty: QuizDifficulty = QuizDifficulty.MEDIUM
    num_questions: int = Field(default=10, ge=1, le=50)
    time_limit_minutes: int | None = Field(default=None, ge=1, le=180)


class QuizAnswerSubmit(BaseSchema):
    question_id: str
    user_answer: str


class QuizSubmitRequest(BaseSchema):
    answers: list[QuizAnswerSubmit] = Field(min_length=1)
    time_taken_seconds: int | None = Field(default=None, ge=0)


class QuizResponse(BaseSchema):
    id: str
    user_id: str
    title: str
    subject: str | None = None
    difficulty: QuizDifficulty | None = None
    source_notes_id: str | None = None
    source_analysis_id: str | None = None
    source_topics: list[str] = []
    quiz_type: QuizType
    questions: list[QuizQuestion]
    total_questions: int
    time_limit_minutes: int | None = None
    created_at: datetime | None = None


class QuizAttemptAnswerResult(BaseSchema):
    question_id: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str | None = None
    topic: str | None = None


class QuizSubmitResponse(BaseSchema):
    attempt_id: str
    quiz_id: str
    subject: str | None = None
    difficulty: QuizDifficulty | None = None
    quiz_title: str | None = None
    score: float
    correct_count: int
    total_count: int
    answers: list[QuizAttemptAnswerResult]
    completed_at: datetime


class QuizAttemptResponse(BaseSchema):
    id: str
    user_id: str
    quiz_id: str
    quiz_title: str | None = None
    subject: str | None = None
    difficulty: QuizDifficulty | None = None
    quiz_type: QuizType | None = None
    score: float
    correct_count: int
    total_count: int
    time_taken_seconds: int | None = None
    completed_at: datetime


class SubjectInfo(BaseSchema):
    name: str
    analysis_count: int = 0
    topic_count: int = 0
    document_count: int = 0


class SubjectTopic(BaseSchema):
    topic: str
    unit: str | None = None
    frequency: int = 1
    importance: str | None = None


class SubjectTopicsResponse(BaseSchema):
    subject: str
    topics: list[SubjectTopic]
    analysis_ids: list[str] = []


class TopicPerformance(BaseSchema):
    topic: str
    subject: str | None = None
    accuracy_percentage: float
    attempts: int
    correct: int
    total: int


class SubjectPerformance(BaseSchema):
    subject: str
    accuracy_percentage: float
    attempts: int
    quizzes: int


class WeeklyProgressPoint(BaseSchema):
    week: str
    average_score: float
    quizzes: int


class ScoreTrendPoint(BaseSchema):
    date: str
    score: float
    subject: str | None = None


class QuizAnalysisResponse(BaseSchema):
    total_quizzes_attempted: int
    average_score: float
    highest_score: float
    lowest_score: float
    total_questions_solved: int
    subject_performance: list[SubjectPerformance]
    weak_topics: list[TopicPerformance]
    strong_topics: list[TopicPerformance]
    improvement_suggestions: list[str]
    weekly_progress: list[WeeklyProgressPoint]
    score_trend: list[ScoreTrendPoint]
    topic_strength_distribution: list[TopicPerformance]
