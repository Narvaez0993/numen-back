from dataclasses import dataclass
from uuid import UUID

from src.modules.categories.application.dto.category import CategoryDTO
from src.modules.categories.application.dto.update_category import UpdateCategoryInputDTO
from src.modules.categories.application.ports.category_repository import CategoryRepository
from src.modules.categories.domain.entities.category import (
    ALLOWED_COLORS,
    MAX_NAME_LENGTH,
    CategoryFlow,
)
from src.modules.categories.domain.errors import (
    CategoryNameTakenError,
    CategoryNotFoundError,
    InvalidCategoryError,
)
from src.modules.categories.domain.standard_catalog import standard_name_exists


@dataclass
class UpdateCategoryUseCase:
    category_repository: CategoryRepository

    async def execute(self, input_dto: UpdateCategoryInputDTO) -> CategoryDTO:
        category = await self.category_repository.find(input_dto.user_id, input_dto.category_id)
        if category is None:
            raise CategoryNotFoundError()

        new_name: str | None = None
        if input_dto.name is not None:
            candidate = input_dto.name.strip()
            if not candidate or len(candidate) > MAX_NAME_LENGTH:
                raise InvalidCategoryError(f"Category name must be 1-{MAX_NAME_LENGTH} characters")
            if candidate.casefold() != category.name.casefold():
                await self._ensure_name_free(
                    input_dto.user_id, category.id, category.flow, candidate
                )
            new_name = candidate

        if input_dto.color is not None and input_dto.color not in ALLOWED_COLORS:
            raise InvalidCategoryError(f"Invalid color: {input_dto.color}")

        new_icon = input_dto.icon.strip() if input_dto.icon is not None else None
        if new_icon is not None and not new_icon:
            raise InvalidCategoryError("Category icon is required")

        updated = category.with_updates(name=new_name, icon=new_icon, color=input_dto.color)
        await self.category_repository.save(updated)
        return CategoryDTO.from_domain(updated)

    async def _ensure_name_free(
        self, user_id: UUID, category_id: str, flow: CategoryFlow, candidate: str
    ) -> None:
        customs = await self.category_repository.list_by_user(user_id)
        lowered = candidate.casefold()
        taken = standard_name_exists(candidate, flow) or any(
            c.id != category_id and c.flow == flow and c.name.casefold() == lowered for c in customs
        )
        if taken:
            raise CategoryNameTakenError()
