from pydantic import BaseModel


class RegisterInputDTO(BaseModel):
    email: str
    password: str
    display_name: str = ""
    language: str | None = None
    currency: str | None = None
    """What the device reports. Unsupported values fall back to the defaults."""


class RegisterOutputDTO(BaseModel):
    user_id: str
    email: str
    display_name: str
    tier: str
    email_verified: bool
