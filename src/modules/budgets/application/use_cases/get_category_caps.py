from dataclasses import dataclass
from datetime import date

from src.modules.budgets.application.dto.budget_commands import CategoryCapsInputDTO
from src.modules.budgets.application.dto.snapshot import CategoryCapProgressDTO
from src.modules.budgets.application.ports.budget_repository import BudgetRepository
from src.modules.budgets.application.ports.spend_reader import SpendReader
from src.modules.budgets.domain import spending_cap
from src.shared.domain.period import MonthPeriod


@dataclass
class GetCategoryCapsUseCase:
    """The category caps measured, for Home — the same figures the Presupuestos screen
    shows, without the work Home has no use for.

    It exists apart from the snapshot for the reason `GetGlobalCapUseCase` does: Home
    reads this on **every** load and needs neither the merchant grouping (one round trip
    per watched category) nor the urgency ordering. And it exists apart from Home doing
    the division itself because `used` belongs to the module that owns the cap: the day
    that number stops being `spent / target`, both screens change together.

    Someone who watches no category pays a single indexed read and nothing else — no
    aggregation runs when there is no cap to measure against.
    """

    budget_repository: BudgetRepository
    spend_reader: SpendReader

    async def execute(self, input_dto: CategoryCapsInputDTO) -> list[CategoryCapProgressDTO]:
        budgets = await self.budget_repository.list_by_user(input_dto.user_id)
        watched = [b for b in budgets if b.scope == "category" and b.category_id is not None]
        if not watched:
            return []

        period = MonthPeriod.containing(date.fromisoformat(input_dto.today))
        by_category = await self.spend_reader.by_category(
            input_dto.user_id, period.first_day, period.last_day
        )
        spend = {row.category_id: row for row in by_category}

        return [
            CategoryCapProgressDTO.for_category(
                cap,
                spending_cap.progress(
                    target=cap.target,
                    # A watched category with no expenses yet is 0 spent, not a missing cap.
                    spent=spend[cap.category_id].spent if cap.category_id in spend else 0,
                    days_left=period.days_left,
                    days_elapsed=period.days_elapsed,
                    total_days=period.total_days,
                ),
            )
            for cap in watched
        ]
