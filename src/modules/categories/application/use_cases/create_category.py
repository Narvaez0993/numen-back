from dataclasses import dataclass
from typing import cast

from src.modules.categories.application.dto.category import CategoryDTO
from src.modules.categories.application.dto.create_category import CreateCategoryInputDTO
from src.modules.categories.application.ports.category_repository import CategoryRepository
from src.modules.categories.domain.entities.category import (
    ALLOWED_COLORS,
    ALLOWED_FLOWS,
    MAX_NAME_LENGTH,
    Category,
    CategoryFlow,
)
from src.modules.categories.domain.errors import (
    CategoryLimitReachedError,
    CategoryNameTakenError,
    InvalidCategoryError,
)
from src.modules.categories.domain.standard_catalog import standard_name_exists


@dataclass
class CreateCategoryUseCase:
    category_repository: CategoryRepository
    free_limit: int

    async def execute(self, input_dto: CreateCategoryInputDTO) -> CategoryDTO:
        name = input_dto.name.strip()
        if not name or len(name) > MAX_NAME_LENGTH:
            raise InvalidCategoryError(f"Category name must be 1-{MAX_NAME_LENGTH} characters")
        if not input_dto.icon.strip():
            raise InvalidCategoryError("Category icon is required")
        if input_dto.flow not in ALLOWED_FLOWS:
            raise InvalidCategoryError(f"Invalid flow: {input_dto.flow}")
        if input_dto.color not in ALLOWED_COLORS:
            raise InvalidCategoryError(f"Invalid color: {input_dto.color}")
        flow = cast(CategoryFlow, input_dto.flow)

        # One indexed read serves both the capacity gate and name dedupe.
        customs = await self.category_repository.list_by_user(input_dto.user_id)
        if input_dto.tier != "plus" and len(customs) >= self.free_limit:
            raise CategoryLimitReachedError()

        lowered = name.casefold()
        duplicate = standard_name_exists(name, flow) or any(
            c.flow == flow and c.name.casefold() == lowered for c in customs
        )
        if duplicate:
            raise CategoryNameTakenError()

        category = Category.create_custom(
            user_id=input_dto.user_id,
            name=name,
            icon=input_dto.icon.strip(),
            color=input_dto.color,
            flow=flow,
        )
        await self.category_repository.save(category)
        return CategoryDTO.from_domain(category)
