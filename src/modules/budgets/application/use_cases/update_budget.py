from dataclasses import dataclass

from src.modules.budgets.application.dto.budget import BudgetDTO
from src.modules.budgets.application.dto.budget_commands import UpdateBudgetInputDTO
from src.modules.budgets.application.ports.budget_repository import BudgetRepository
from src.modules.budgets.domain.entities.budget import MAX_TARGET, MIN_TARGET
from src.modules.budgets.domain.errors import BudgetNotFoundError, InvalidBudgetError


@dataclass
class UpdateBudgetUseCase:
    """Changes the number, and stamps the month of the change.

    The new value applies from now on — including the month in progress, which is the
    point: someone who realises on the 12th that $2M was unrealistic is telling us what
    to measure the rest of July against, not filing a correction for August.
    """

    budget_repository: BudgetRepository

    async def execute(self, input_dto: UpdateBudgetInputDTO) -> BudgetDTO:
        if not MIN_TARGET <= input_dto.target <= MAX_TARGET:
            raise InvalidBudgetError("A cap has to be a positive amount")

        budget = await self.budget_repository.find(input_dto.user_id, input_dto.budget_id)
        if budget is None:
            raise BudgetNotFoundError()

        updated = budget.retargeted(target=input_dto.target, since=input_dto.today[:7])
        await self.budget_repository.save(updated)
        return BudgetDTO.from_domain(updated)
