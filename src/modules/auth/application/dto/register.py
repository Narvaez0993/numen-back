from pydantic import BaseModel


class RegisterInputDTO(BaseModel):
    email: str
    password: str
    display_name: str = ""


class RegisterOutputDTO(BaseModel):
    user_id: str
    email: str
    display_name: str
    tier: str
    email_verified: bool
