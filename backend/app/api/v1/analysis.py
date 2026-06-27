from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.api.deps import get_analysis_service
from app.core.dependencies import get_current_user
from app.core.responses import paginated_response, success_response
from app.schemas.analysis import PYQAnalysisCreateRequest
from app.schemas.common import PaginationParams
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analysis/pyq", tags=["PYQ Analysis"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start PYQ analysis on uploaded documents",
)
async def create_pyq_analysis(
    payload: PYQAnalysisCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    analysis_service: Annotated[AnalysisService, Depends(get_analysis_service)],
):
    data = await analysis_service.create_analysis(
        str(current_user["_id"]),
        payload.document_ids,
        subject=payload.subject,
        title=payload.title,
        background_tasks=background_tasks,
    )
    return success_response(data, "Analysis started")


@router.get("", summary="List PYQ analyses")
async def list_pyq_analyses(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    analysis_service: Annotated[AnalysisService, Depends(get_analysis_service)],
    pagination: Annotated[PaginationParams, Depends()],
):
    analyses, total = await analysis_service.list_analyses(
        str(current_user["_id"]),
        page=pagination.page,
        limit=pagination.limit,
    )
    return paginated_response(analyses, pagination.page, pagination.limit, total)


@router.get("/{analysis_id}", summary="Get PYQ analysis result")
async def get_pyq_analysis(
    analysis_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    analysis_service: Annotated[AnalysisService, Depends(get_analysis_service)],
):
    data = await analysis_service.get_analysis(analysis_id, str(current_user["_id"]))
    return success_response(data)


@router.get("/{analysis_id}/status", summary="Get PYQ analysis processing status")
async def get_pyq_analysis_status(
    analysis_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    analysis_service: Annotated[AnalysisService, Depends(get_analysis_service)],
):
    data = await analysis_service.get_analysis_status(analysis_id, str(current_user["_id"]))
    return success_response(data)


@router.delete("/{analysis_id}", summary="Delete PYQ analysis")
async def delete_pyq_analysis(
    analysis_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    analysis_service: Annotated[AnalysisService, Depends(get_analysis_service)],
):
    await analysis_service.delete_analysis(analysis_id, str(current_user["_id"]))
    return success_response({"message": "Analysis deleted successfully"})
