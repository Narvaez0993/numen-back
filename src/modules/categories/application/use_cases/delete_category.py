from dataclasses import dataclass

from src.modules.categories.application.dto.delete_category import DeleteCategoryInputDTO
from src.modules.categories.application.ports.category_repository import CategoryRepository
from src.modules.categories.domain.errors import CategoryNotFoundError


@dataclass
class DeleteCategoryUseCase:
    category_repository: CategoryRepository

    async def execute(self, input_dto: DeleteCategoryInputDTO) -> None:
        category = await self.category_repository.find(input_dto.user_id, input_dto.category_id)
        if category is None:
            raise CategoryNotFoundError()
        await self.category_repository.delete(input_dto.user_id, input_dto.category_id)
