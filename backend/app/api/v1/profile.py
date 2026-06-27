from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_profile_service
from app.core.dependencies import get_current_user
from app.core.responses import success_response
from app.schemas.profile import (
    ChangePasswordRequest,
    PreferencesUpdateRequest,
    ProfileUpdateRequest,
)
from app.services.profile_service import ProfileService

router = APIRouter(tags=["Profile & Dashboard"])


@router.get("/dashboard", summary="Get user dashboard stats")
async def get_dashboard(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
):
    data = await profile_service.get_dashboard(str(current_user["_id"]))
    return success_response(data)


@router.delete("/dashboard/activities", summary="Clear all recent activity")
async def clear_dashboard_activities(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
):
    data = await profile_service.clear_recent_activity(str(current_user["_id"]))
    return success_response(data, "Recent activity cleared")


@router.delete("/dashboard/activities/{ref_id}", summary="Delete a recent activity item")
async def delete_dashboard_activity(
    ref_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
    activity_type: Annotated[str, Query(alias="type", min_length=1)],
):
    data = await profile_service.delete_recent_activity(
        str(current_user["_id"]),
        ref_id=ref_id,
        activity_type=activity_type,
    )
    return success_response(data, "Activity removed")


@router.get("/profile", summary="Get user profile")
async def get_profile(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
):
    data = await profile_service.get_profile(current_user)
    return success_response(data)


@router.patch("/profile", summary="Update user profile")
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
):
    data = await profile_service.update_profile(str(current_user["_id"]), payload.model_dump())
    return success_response(data, "Profile updated")


@router.patch("/profile/preferences", summary="Update user preferences")
async def update_preferences(
    payload: PreferencesUpdateRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
):
    data = await profile_service.update_preferences(
        str(current_user["_id"]),
        payload.preferences.model_dump(),
    )
    return success_response(data, "Preferences updated")


@router.patch("/profile/password", summary="Change password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
):
    data = await profile_service.change_password(
        current_user,
        payload.current_password,
        payload.new_password,
    )
    return success_response(data)


@router.delete("/profile", summary="Delete user account")
async def delete_account(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
):
    await profile_service.delete_account(str(current_user["_id"]))
    return success_response({"message": "Account deleted successfully"})
