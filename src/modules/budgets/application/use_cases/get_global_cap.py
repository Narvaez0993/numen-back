from dataclasses import dataclass
from datetime import date

from src.modules.budgets.application.dto.budget import CapDTO
from src.modules.budgets.application.dto.budget_commands import GlobalCapInputDTO
from src.modules.budgets.application.ports.budget_repository import BudgetRepository
from src.modules.budgets.application.ports.spend_reader import SpendReader
from src.modules.budgets.domain import spending_cap
from src.shared.domain.period import MonthPeriod


@dataclass
class GetGlobalCapUseCase:
    """The month's ceiling on its own, for Home.

    It exists apart from the snapshot because Home reads it on **every** load and needs
    none of the rest: one indexed document plus one aggregation, instead of the per
    category spend and the merchant grouping the Presupuestos screen asks for.

    `None` when the user has not set a ceiling — Home then falls back to the pace, and
    never to a $0 cap.
    """

    budget_repository: BudgetRepository
    spend_reader: SpendReader

    async def execute(self, input_dto: GlobalCapInputDTO) -> CapDTO | None:
        budget = await self.budget_repository.find_global(input_dto.user_id)
        if budget is None:
            return None

        period = MonthPeriod.containing(date.fromisoformat(input_dto.today))
        spent = await self.spend_reader.spent(input_dto.user_id, period.first_day, period.last_day)
        return CapDTO.build(
            budget,
            spending_cap.progress(
                target=budget.target,
                spent=spent,
                days_left=period.days_left,
                days_elapsed=period.days_elapsed,
                total_days=period.total_days,
            ),
        )
