from uuid import UUID

from pydantic import BaseModel


class CreateCategoryInputDTO(BaseModel):
    user_id: UUID
    tier: str
    name: str
    icon: str
    color: str
    flow: str
