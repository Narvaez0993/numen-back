from uuid import UUID

from pydantic import BaseModel

from src.modules.categories.application.dto.category import CategoryDTO


class ListCategoriesInputDTO(BaseModel):
    user_id: UUID


class ListCategoriesOutputDTO(BaseModel):
    categories: list[CategoryDTO]
