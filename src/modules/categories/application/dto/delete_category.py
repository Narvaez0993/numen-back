from uuid import UUID

from pydantic import BaseModel


class DeleteCategoryInputDTO(BaseModel):
    user_id: UUID
    category_id: str
