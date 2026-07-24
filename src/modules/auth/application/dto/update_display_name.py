from uuid import UUID

from pydantic import BaseModel


class UpdateDisplayNameInputDTO(BaseModel):
    user_id: UUID
    display_name: str


class UpdateDisplayNameOutputDTO(BaseModel):
    user_id: str
    email: str
    display_name: str
    tier: str
    email_verified: bool
