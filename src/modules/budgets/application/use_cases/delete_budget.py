from dataclasses import dataclass

from src.modules.budgets.application.dto.budget_commands import DeleteBudgetInputDTO
from src.modules.budgets.application.ports.budget_repository import BudgetRepository
from src.modules.budgets.domain.errors import BudgetNotFoundError


@dataclass
class DeleteBudgetUseCase:
    """Stops watching. Nothing else is touched: a cap never held money, so removing it
    cannot change a balance or a movement — it only takes the ceiling off the screens
    that were measuring against it."""

    budget_repository: BudgetRepository

    async def execute(self, input_dto: DeleteBudgetInputDTO) -> None:
        budget = await self.budget_repository.find(input_dto.user_id, input_dto.budget_id)
        if budget is None:
            raise BudgetNotFoundError()
        await self.budget_repository.delete(input_dto.user_id, input_dto.budget_id)
