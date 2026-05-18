from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class AuthResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    tier: str
    access_token: str


class CurrentUserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    tier: str
