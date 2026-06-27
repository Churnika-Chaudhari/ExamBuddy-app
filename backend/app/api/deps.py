from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.dependencies import get_db
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.generated_notes_repository import GeneratedNotesRepository
from app.repositories.notes_repository import NotesRepository
from app.repositories.quiz_repository import (
    QuizAnalysisRepository,
    QuizAttemptRepository,
    QuizRepository,
)
from app.repositories.stats_repository import StatsRepository
from app.repositories.subject_repository import SubjectRepository
from app.repositories.user_repository import UserRepository
from app.services.ai.ai_service import AIService
from app.services.analysis_service import AnalysisService
from app.services.auth_service import AuthService
from app.services.document_service import DocumentService
from app.services.file_service import FileService
from app.services.notes_service import NotesService
from app.services.profile_service import ProfileService
from app.services.quiz_service import QuizService
from app.services.subject_service import SubjectService


def get_user_repo(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> UserRepository:
    return UserRepository(db)


def get_document_repo(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> DocumentRepository:
    return DocumentRepository(db)


def get_analysis_repo(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> AnalysisRepository:
    return AnalysisRepository(db)


def get_notes_repo(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> NotesRepository:
    return NotesRepository(db)


def get_quiz_repo(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> QuizRepository:
    return QuizRepository(db)


def get_attempt_repo(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> QuizAttemptRepository:
    return QuizAttemptRepository(db)


def get_stats_repo(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> StatsRepository:
    return StatsRepository(db)


def get_file_service() -> FileService:
    return FileService()


def get_ai_service() -> AIService:
    return AIService()


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> AuthService:
    return AuthService(user_repo)


def get_subject_repo(db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]) -> SubjectRepository:
    return SubjectRepository(db)


def get_subject_service(
    subject_repo: Annotated[SubjectRepository, Depends(get_subject_repo)],
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
    analysis_repo: Annotated[AnalysisRepository, Depends(get_analysis_repo)],
) -> SubjectService:
    return SubjectService(subject_repo, document_repo, analysis_repo)


def get_document_service(
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
    stats_repo: Annotated[StatsRepository, Depends(get_stats_repo)],
    file_service: Annotated[FileService, Depends(get_file_service)],
    subject_service: Annotated[SubjectService, Depends(get_subject_service)],
) -> DocumentService:
    return DocumentService(document_repo, stats_repo, file_service, subject_service)


def get_analysis_service(
    analysis_repo: Annotated[AnalysisRepository, Depends(get_analysis_repo)],
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
    stats_repo: Annotated[StatsRepository, Depends(get_stats_repo)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    subject_service: Annotated[SubjectService, Depends(get_subject_service)],
) -> AnalysisService:
    return AnalysisService(analysis_repo, document_repo, stats_repo, ai_service, subject_service)


def get_generated_notes_repo(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
) -> GeneratedNotesRepository:
    return GeneratedNotesRepository(db)


def get_notes_service(
    notes_repo: Annotated[NotesRepository, Depends(get_notes_repo)],
    analysis_repo: Annotated[AnalysisRepository, Depends(get_analysis_repo)],
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
    stats_repo: Annotated[StatsRepository, Depends(get_stats_repo)],
    generated_notes_repo: Annotated[GeneratedNotesRepository, Depends(get_generated_notes_repo)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> NotesService:
    return NotesService(
        notes_repo, analysis_repo, document_repo, stats_repo, generated_notes_repo, ai_service
    )


def get_quiz_analysis_repo(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
) -> QuizAnalysisRepository:
    return QuizAnalysisRepository(db)


def get_quiz_service(
    quiz_repo: Annotated[QuizRepository, Depends(get_quiz_repo)],
    attempt_repo: Annotated[QuizAttemptRepository, Depends(get_attempt_repo)],
    analysis_repo: Annotated[AnalysisRepository, Depends(get_analysis_repo)],
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
    generated_notes_repo: Annotated[GeneratedNotesRepository, Depends(get_generated_notes_repo)],
    notes_repo: Annotated[NotesRepository, Depends(get_notes_repo)],
    stats_repo: Annotated[StatsRepository, Depends(get_stats_repo)],
    quiz_analysis_repo: Annotated[QuizAnalysisRepository, Depends(get_quiz_analysis_repo)],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> QuizService:
    return QuizService(
        quiz_repo,
        attempt_repo,
        analysis_repo,
        document_repo,
        generated_notes_repo,
        notes_repo,
        stats_repo,
        quiz_analysis_repo,
        ai_service,
    )


def get_profile_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    stats_repo: Annotated[StatsRepository, Depends(get_stats_repo)],
    document_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
    analysis_repo: Annotated[AnalysisRepository, Depends(get_analysis_repo)],
    notes_repo: Annotated[NotesRepository, Depends(get_notes_repo)],
    attempt_repo: Annotated[QuizAttemptRepository, Depends(get_attempt_repo)],
    file_service: Annotated[FileService, Depends(get_file_service)],
) -> ProfileService:
    return ProfileService(
        user_repo,
        stats_repo,
        document_repo,
        analysis_repo,
        notes_repo,
        attempt_repo,
        file_service,
    )
