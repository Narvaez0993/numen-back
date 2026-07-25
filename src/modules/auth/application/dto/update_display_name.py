from uuid import UUID

from pydantic import BaseModel


class UpdateDisplayNameInputDTO(BaseModel):
    user_id: UUID
    display_name: str
