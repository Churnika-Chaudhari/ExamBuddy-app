from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import BaseSchema


class UserRegisterRequest(BaseSchema):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isalpha() for char in value):
            raise ValueError("Password must contain at least one letter")
        return value


class UserLoginRequest(BaseSchema):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseSchema):
    email: EmailStr


class ResetPasswordRequest(BaseSchema):
    token: str = Field(min_length=10)
    new_password: str = Field(min_length=8, max_length=128)


class RefreshTokenRequest(BaseSchema):
    refresh_token: str


class UserPreferences(BaseSchema):
    ai_provider: str | None = "openai"
    theme: str | None = "light"
    notifications: bool = True


class UserResponse(BaseSchema):
    id: str
    email: EmailStr
    full_name: str
    avatar_url: str | None = None
    institution: str | None = None
    course: str | None = None
    preferences: UserPreferences | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class AuthResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
