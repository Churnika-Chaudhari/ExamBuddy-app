import secrets
from datetime import UTC, datetime
from typing import Annotated, Any

from bson import ObjectId
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token, verify_token_type
from app.db.mongodb import get_database
from app.repositories.user_repository import UserRepository

security_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncIOMotorDatabase:
    return get_database()


async def get_user_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_db)],
) -> UserRepository:
    return UserRepository(db)


async def get_current_user_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Missing or invalid authorization header")

    try:
        payload = decode_token(credentials.credentials)
        verify_token_type(payload, "access")
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

    return payload


async def get_current_user(
    payload: Annotated[dict[str, Any], Depends(get_current_user_payload)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> dict[str, Any]:
    user_id = payload.get("sub")
    if not user_id or not ObjectId.is_valid(user_id):
        raise UnauthorizedError("Invalid token subject")

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise UnauthorizedError("User not found")
    if not user.get("is_active", True):
        raise UnauthorizedError("Account is deactivated")

    return user


async def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> dict[str, Any] | None:
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        verify_token_type(payload, "access")
        user_id = payload.get("sub")
        if not user_id or not ObjectId.is_valid(user_id):
            return None
        return await user_repo.get_by_id(user_id)
    except JWTError:
        return None


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def utc_now() -> datetime:
    return datetime.now(UTC)
