from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=80)


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
    access_token: str
    refresh_token: str


class CurrentUserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    tier: str
    email_verified: bool
