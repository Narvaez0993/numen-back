import asyncio
from dataclasses import dataclass
from datetime import date

from src.modules.budgets.application.dto.budget import CapDTO
from src.modules.budgets.application.dto.budget_commands import BudgetsSnapshotInputDTO
from src.modules.budgets.application.dto.snapshot import BudgetsSnapshotDTO, CategoryCapDTO
from src.modules.budgets.application.ports.budget_repository import BudgetRepository
from src.modules.budgets.application.ports.spend_reader import SpendReader
from src.modules.budgets.domain import spending_cap
from src.modules.budgets.domain.entities.budget import Budget
from src.shared.domain.period import MonthPeriod

# Enough to answer "where did it go" without turning the row into a second movements
# list — the row links to the filtered list for the rest.
TOP_MERCHANTS = 3


@dataclass
class GetBudgetsSnapshotUseCase:
    """The Presupuestos screen: the ceiling, the watched categories and where their
    money went.

    Only categories the user put a cap on are computed. Everything else is spending they
    chose not to watch, and a cap the app invents is not a cap.
    """

    budget_repository: BudgetRepository
    spend_reader: SpendReader

    async def execute(self, input_dto: BudgetsSnapshotInputDTO) -> BudgetsSnapshotDTO:
        period = MonthPeriod.containing(date.fromisoformat(input_dto.today))
        budgets = await self.budget_repository.list_by_user(input_dto.user_id)

        by_category = await self.spend_reader.by_category(
            input_dto.user_id, period.first_day, period.last_day
        )
        spend = {row.category_id: row for row in by_category}
        # The month's expenses, without a second aggregation: the grouping already
        # covers every expense in the range, unclassified included.
        month_spent = sum(row.spent for row in by_category)

        watched = [b for b in budgets if b.scope == "category" and b.category_id is not None]
        # One round trip per watched category, in parallel: Free allows two of them and
        # Plus a handful, so the fan-out is bounded by the plan, not by the history.
        merchants = await asyncio.gather(
            *(
                self.spend_reader.top_merchants(
                    input_dto.user_id,
                    period.first_day,
                    period.last_day,
                    cap.category_id,
                    TOP_MERCHANTS,
                )
                for cap in watched
            )
        )

        categories: list[CategoryCapDTO] = []
        for cap, rows in zip(watched, merchants, strict=True):
            # A watched category with no expenses yet is 0 spent, not a missing row.
            row = spend.get(cap.category_id)
            categories.append(
                CategoryCapDTO.for_category(
                    cap,
                    self._progress(cap, spent=row.spent if row else 0, period=period),
                    count=row.count if row else 0,
                    merchants=list(rows),
                )
            )
        # Most urgent first: the closest to its cap, not the biggest number.
        categories.sort(key=lambda category: category.used, reverse=True)

        month = next((b for b in budgets if b.scope == "global"), None)
        return BudgetsSnapshotDTO(
            currency=input_dto.currency,
            period=period.key,
            days_left=period.days_left,
            days_elapsed=period.days_elapsed,
            month=(
                None
                if month is None
                else CapDTO.build(month, self._progress(month, spent=month_spent, period=period))
            ),
            categories=categories,
        )

    @staticmethod
    def _progress(budget: Budget, *, spent: int, period: MonthPeriod) -> spending_cap.CapProgress:
        return spending_cap.progress(
            target=budget.target,
            spent=spent,
            days_left=period.days_left,
            days_elapsed=period.days_elapsed,
            total_days=period.total_days,
        )
