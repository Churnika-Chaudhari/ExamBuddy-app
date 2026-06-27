from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_quiz_service
from app.core.dependencies import get_current_user
from app.core.responses import paginated_response, success_response
from app.schemas.common import PaginationParams
from app.schemas.quiz import (
    QuizGenerateRequest,
    QuizSubmitRequest,
)
from app.services.quiz_service import QuizService

router = APIRouter(prefix="/quiz", tags=["Quiz"])


@router.get("/history", summary="List quiz attempt history")
async def list_quiz_history(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    quiz_service: Annotated[QuizService, Depends(get_quiz_service)],
    pagination: Annotated[PaginationParams, Depends()],
    subject: str | None = None,
    search: str | None = None,
):
    attempts, total = await quiz_service.list_attempt_history(
        str(current_user["_id"]),
        page=pagination.page,
        limit=pagination.limit,
        subject=subject,
        search=search,
    )
    return paginated_response(attempts, pagination.page, pagination.limit, total)


@router.get("/analysis/{subject}", summary="Subject-wise quiz performance analysis")
async def get_quiz_analysis_by_subject(
    subject: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    quiz_service: Annotated[QuizService, Depends(get_quiz_service)],
):
    data = await quiz_service.get_quiz_analysis(str(current_user["_id"]), subject=subject)
    return success_response(data)


@router.get("/attempts/{attempt_id}", summary="Get quiz attempt details")
async def get_quiz_attempt(
    attempt_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    quiz_service: Annotated[QuizService, Depends(get_quiz_service)],
):
    data = await quiz_service.get_attempt(attempt_id, str(current_user["_id"]))
    return success_response(data)


@router.delete("/attempts/{attempt_id}", summary="Delete quiz attempt from history")
async def delete_quiz_attempt(
    attempt_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    quiz_service: Annotated[QuizService, Depends(get_quiz_service)],
):
    await quiz_service.delete_attempt(attempt_id, str(current_user["_id"]))
    return success_response({"message": "Attempt deleted"})


@router.post(
    "/generate",
    status_code=status.HTTP_201_CREATED,
    summary="Generate AI quiz from subject topics, notes, or topic list",
)
async def generate_quiz(
    payload: QuizGenerateRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    quiz_service: Annotated[QuizService, Depends(get_quiz_service)],
):
    data = await quiz_service.generate_quiz(
        str(current_user["_id"]),
        notes_id=payload.notes_id,
        analysis_id=payload.analysis_id,
        subject=payload.subject,
        topics=payload.topics,
        title=payload.title,
        quiz_type=payload.quiz_type,
        difficulty=payload.difficulty,
        num_questions=payload.num_questions,
        time_limit_minutes=payload.time_limit_minutes,
    )
    return success_response(data, "Quiz generated successfully")


@router.get("", summary="List user quizzes")
async def list_quizzes(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    quiz_service: Annotated[QuizService, Depends(get_quiz_service)],
    pagination: Annotated[PaginationParams, Depends()],
    subject: str | None = None,
):
    quizzes, total = await quiz_service.list_quizzes(
        str(current_user["_id"]),
        page=pagination.page,
        limit=pagination.limit,
        subject=subject,
    )
    return paginated_response(quizzes, pagination.page, pagination.limit, total)


@router.delete("", summary="Clear all generated quizzes (recent quiz list)")
async def clear_quizzes(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    quiz_service: Annotated[QuizService, Depends(get_quiz_service)],
):
    deleted = await quiz_service.clear_quizzes(str(current_user["_id"]))
    return success_response({"deleted": deleted, "message": "Recent quizzes cleared"})


@router.get("/{quiz_id}", summary="Get quiz by ID")
async def get_quiz(
    quiz_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    quiz_service: Annotated[QuizService, Depends(get_quiz_service)],
):
    data = await quiz_service.get_quiz(quiz_id, str(current_user["_id"]))
    return success_response(data)


@router.post("/{quiz_id}/submit", summary="Submit quiz answers and get score")
async def submit_quiz(
    quiz_id: str,
    payload: QuizSubmitRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    quiz_service: Annotated[QuizService, Depends(get_quiz_service)],
):
    answers = [answer.model_dump() for answer in payload.answers]
    data = await quiz_service.submit_quiz(
        quiz_id,
        str(current_user["_id"]),
        answers,
        payload.time_taken_seconds,
    )
    return success_response(data, "Quiz submitted successfully")


@router.get("/{quiz_id}/attempts", summary="Get quiz attempt history")
async def get_quiz_attempts(
    quiz_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    quiz_service: Annotated[QuizService, Depends(get_quiz_service)],
):
    data = await quiz_service.get_quiz_attempts(quiz_id, str(current_user["_id"]))
    return success_response(data)


@router.delete("/{quiz_id}", summary="Delete quiz")
async def delete_quiz(
    quiz_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    quiz_service: Annotated[QuizService, Depends(get_quiz_service)],
):
    await quiz_service.delete_quiz(quiz_id, str(current_user["_id"]))
    return success_response({"message": "Quiz deleted successfully"})
