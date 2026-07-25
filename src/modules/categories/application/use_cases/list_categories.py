from dataclasses import dataclass

from src.modules.categories.application.dto.category import CategoryDTO
from src.modules.categories.application.dto.list_categories import (
    ListCategoriesInputDTO,
    ListCategoriesOutputDTO,
)
from src.modules.categories.application.ports.category_repository import CategoryRepository
from src.modules.categories.domain.standard_catalog import STANDARD_CATEGORIES


@dataclass
class ListCategoriesUseCase:
    category_repository: CategoryRepository

    async def execute(self, input_dto: ListCategoriesInputDTO) -> ListCategoriesOutputDTO:
        custom = await self.category_repository.list_by_user(input_dto.user_id)
        categories = [CategoryDTO.from_domain(c) for c in STANDARD_CATEGORIES]
        categories.extend(CategoryDTO.from_domain(c) for c in custom)
        return ListCategoriesOutputDTO(categories=categories)
