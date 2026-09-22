from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.deps import get_syllabus_service
from app.core.dependencies import get_current_user
from app.core.responses import success_response
from app.services.syllabus_service import SyllabusService

router = APIRouter(prefix="/syllabus", tags=["Syllabus"])


@router.get("", summary="List saved syllabi for the current user")
async def list_syllabi(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    syllabus_service: Annotated[SyllabusService, Depends(get_syllabus_service)],
):
    data = await syllabus_service.list_syllabi(str(current_user["_id"]))
    return success_response({"syllabi": data, "count": len(data)})


@router.get("/{subject}", summary="Get the saved syllabus for one subject")
async def get_syllabus(
    subject: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    syllabus_service: Annotated[SyllabusService, Depends(get_syllabus_service)],
):
    data = await syllabus_service.get_for_subject(str(current_user["_id"]), subject)
    return success_response(data)


@router.delete("/id/{syllabus_id}", summary="Delete a saved syllabus")
async def delete_syllabus(
    syllabus_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    syllabus_service: Annotated[SyllabusService, Depends(get_syllabus_service)],
):
    await syllabus_service.delete_syllabus(str(current_user["_id"]), syllabus_id)
    return success_response({"message": "Syllabus deleted"})
