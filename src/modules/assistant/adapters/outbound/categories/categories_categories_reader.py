from dataclasses import dataclass
from uuid import UUID

from src.modules.assistant.application.ports.categories_reader import CategoryView
from src.modules.categories.application.dto.list_categories import ListCategoriesInputDTO
from src.modules.categories.application.use_cases.list_categories import ListCategoriesUseCase


@dataclass
class CategoriesCategoriesReader:
    """`CategoriesReader` backed by categories — standard + custom, one list."""

    list_categories: ListCategoriesUseCase

    async def all(self, user_id: UUID) -> tuple[CategoryView, ...]:
        output = await self.list_categories.execute(ListCategoriesInputDTO(user_id=user_id))
        return tuple(CategoryView(id=c.id, name=c.name, flow=c.flow) for c in output.categories)
