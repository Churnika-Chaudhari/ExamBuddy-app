from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_subject_service
from app.core.dependencies import get_current_user
from app.core.responses import success_response
from app.schemas.subject import SubjectPyqFilterRequest
from app.services.subject_service import SubjectService

router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.get("", summary="List subjects detected from uploaded PYQs")
async def list_subjects(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    subject_service: Annotated[SubjectService, Depends(get_subject_service)],
):
    data = await subject_service.list_subjects(str(current_user["_id"]))
    return success_response(data)


@router.get("/{subject_id}/topics", summary="Get extracted topics for a subject")
async def get_subject_topics(
    subject_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    subject_service: Annotated[SubjectService, Depends(get_subject_service)],
):
    data = await subject_service.get_subject_topics(str(current_user["_id"]), subject_id)
    return success_response(data)


@router.get("/{subject_id}/overview", summary="Consolidated subject notes overview (topics + sources)")
async def get_subject_overview(
    subject_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    subject_service: Annotated[SubjectService, Depends(get_subject_service)],
):
    data = await subject_service.get_subject_overview(str(current_user["_id"]), subject_id)
    return success_response(data)


@router.get("/{subject_id}/pyq", summary="Filter analyzed PYQ topics by one or more module IDs")
async def get_subject_pyq(
    subject_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    subject_service: Annotated[SubjectService, Depends(get_subject_service)],
    module_ids: Annotated[str | None, Query(description="Comma-separated syllabus module IDs")] = None,
    include_unmapped: Annotated[bool | None, Query()] = None,
):
    data = await subject_service.filter_subject_pyq(
        str(current_user["_id"]),
        subject_id,
        module_ids=module_ids,
        include_unmapped=include_unmapped,
    )
    return success_response(data)


@router.post("/{subject_id}/pyq/filter", summary="Filter analyzed PYQ topics by module ID list")
async def post_subject_pyq_filter(
    subject_id: str,
    payload: SubjectPyqFilterRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    subject_service: Annotated[SubjectService, Depends(get_subject_service)],
):
    data = await subject_service.filter_subject_pyq(
        str(current_user["_id"]),
        subject_id,
        module_ids=payload.module_ids,
        include_unmapped=payload.include_unmapped,
    )
    return success_response(data)


@router.delete("/{subject_id}", summary="Remove a subject from the list")
async def delete_subject(
    subject_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    subject_service: Annotated[SubjectService, Depends(get_subject_service)],
):
    await subject_service.hide_subject(str(current_user["_id"]), subject_id)
    return success_response({"message": "Subject removed"})
