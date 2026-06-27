from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_service
from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.core.responses import success_response
from app.schemas.auth import (
    ForgotPasswordRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    UserLoginRequest,
    UserRegisterRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: UserRegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    data = await auth_service.register(payload.email, payload.password, payload.full_name)
    return success_response(data, "Registration successful")


@router.post("/login", summary="Login user")
async def login(
    payload: UserLoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    data = await auth_service.login(payload.email, payload.password)
    return success_response(data, "Login successful")


@router.post("/refresh", summary="Refresh access token")
async def refresh_token(
    payload: RefreshTokenRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    data = await auth_service.refresh_token(payload.refresh_token)
    return success_response(data, "Token refreshed")


@router.post("/forgot-password", summary="Request password reset")
async def forgot_password(
    payload: ForgotPasswordRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    data = await auth_service.forgot_password(payload.email, settings.frontend_reset_url)
    return success_response(data)


@router.post("/reset-password", summary="Reset password with token")
async def reset_password(
    payload: ResetPasswordRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    data = await auth_service.reset_password(payload.token, payload.new_password)
    return success_response(data)


@router.get("/me", summary="Get current authenticated user")
async def get_me(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    data = await auth_service.get_current_user_profile(current_user)
    return success_response(data)
