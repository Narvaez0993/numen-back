from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    # Optional: the name is collected after email verification and set via
    # PATCH /auth/me.
    display_name: str = Field(default="", max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=1, max_length=12)


class ResendCodeRequest(BaseModel):
    email: EmailStr


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class PendingVerificationResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    tier: str
    email_verified: bool


class AuthResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    tier: str
    language: str
    currency: str
    theme: str
    access_token: str
    refresh_token: str


class CurrentUserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    tier: str
    email_verified: bool
    language: str
    currency: str
    theme: str


class UpdateMeRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)


class UpdatePreferencesRequest(BaseModel):
    """Partial: omitted fields keep their stored value."""

    language: str | None = Field(default=None, max_length=8)
    currency: str | None = Field(default=None, max_length=3)
    theme: str | None = Field(default=None, max_length=8)
