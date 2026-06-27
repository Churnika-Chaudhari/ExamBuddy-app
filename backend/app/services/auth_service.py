import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError

from app.core.dependencies import generate_reset_token
from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError, ValidationAppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
    verify_token_type,
)
from app.repositories.user_repository import UserRepository
from app.services.mappers import map_user_response
from app.utils.email import send_password_reset_email


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def register(self, email: str, password: str, full_name: str) -> dict[str, Any]:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ConflictError("Email is already registered")

        now = datetime.now(UTC)
        user = await self.user_repo.create(
            {
                "email": email.lower(),
                "password_hash": get_password_hash(password),
                "full_name": full_name,
                "avatar_url": None,
                "institution": None,
                "course": None,
                "preferences": {"ai_provider": "openai", "theme": "light", "notifications": True},
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
        )
        return self._build_token_response(user)

    async def login(self, email: str, password: str) -> dict[str, Any]:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user["password_hash"]):
            raise UnauthorizedError("Invalid email or password")
        if not user.get("is_active", True):
            raise UnauthorizedError("Account is deactivated")
        return self._build_token_response(user)

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        try:
            payload = decode_token(refresh_token)
            verify_token_type(payload, "refresh")
        except JWTError as exc:
            raise UnauthorizedError("Invalid refresh token") from exc

        user_id = payload.get("sub")
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UnauthorizedError("User not found")

        return self._build_token_response(user)

    async def get_current_user_profile(self, user: dict[str, Any]) -> dict[str, Any]:
        return map_user_response(user)

    async def forgot_password(self, email: str, reset_url: str) -> dict[str, str]:
        user = await self.user_repo.get_by_email(email)
        if user:
            token = generate_reset_token()
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            expires = datetime.now(UTC) + timedelta(hours=1)
            await self.user_repo.set_reset_token(str(user["_id"]), token_hash, expires)
            await send_password_reset_email(email, token, reset_url)
        return {"message": "If the email exists, a reset link has been sent."}

    async def reset_password(self, token: str, new_password: str) -> dict[str, str]:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        user = await self.user_repo.get_by_reset_token_hash(token_hash)

        if not user:
            raise ValidationAppError("Invalid or expired reset token")

        expires = user.get("reset_token_expires")
        if not expires or expires < datetime.now(UTC):
            raise ValidationAppError("Invalid or expired reset token")

        await self.user_repo.update(
            str(user["_id"]),
            {"password_hash": get_password_hash(new_password)},
        )
        await self.user_repo.clear_reset_token(str(user["_id"]))
        return {"message": "Password reset successfully"}

    def _build_token_response(self, user: dict[str, Any]) -> dict[str, Any]:
        user_id = str(user["_id"])
        access_token = create_access_token(user_id, {"email": user["email"]})
        refresh_token = create_refresh_token(user_id)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": map_user_response(user),
        }
