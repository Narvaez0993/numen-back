from uuid import UUID

from pydantic import BaseModel


class UpdateCategoryInputDTO(BaseModel):
    user_id: UUID
    category_id: str
    name: str | None = None
    icon: str | None = None
    color: str | None = None
