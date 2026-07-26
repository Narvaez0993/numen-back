from dataclasses import dataclass
from datetime import date

from src.modules.overview.application.dto.home_overview import (
    DailyDTO,
    HomeOverviewInputDTO,
    HomeOverviewOutputDTO,
    MonthDTO,
    RecentMovementDTO,
    TopCategoryDTO,
)
from src.modules.overview.application.ports.balance_reader import BalanceReader
from src.modules.overview.application.ports.movement_summary_reader import (
    MovementSummaryReader,
    PeriodSummary,
)
from src.modules.overview.domain import daily_allowance
from src.modules.overview.domain.period import MonthPeriod

TOP_CATEGORIES = 4
RECENT_MOVEMENTS = 5


@dataclass
class GetHomeOverviewUseCase:
    """Composes the Home screen out of what the other modules already know.

    The only place in the backend that reads across modules, and it does it
    through its own ports — so Home can grow (budgets, goals) without any module
    learning about another.
    """

    balance_reader: BalanceReader
    movement_summary_reader: MovementSummaryReader

    async def execute(self, input_dto: HomeOverviewInputDTO) -> HomeOverviewOutputDTO:
        period = MonthPeriod.containing(date.fromisoformat(input_dto.today))

        balance = await self.balance_reader.read(input_dto.user_id, input_dto.currency)
        month = await self.movement_summary_reader.summary(
            input_dto.user_id, period.first_day, period.last_day
        )
        # A single day is a range of one; no special port method for it.
        today = await self.movement_summary_reader.summary(
            input_dto.user_id, input_dto.today, input_dto.today
        )
        recent = await self.movement_summary_reader.recent(input_dto.user_id, RECENT_MOVEMENTS)

        allowance = daily_allowance.compute(
            spent=month.expense_total,
            income=month.income_total,
            days_left=period.days_left,
        )

        return HomeOverviewOutputDTO(
            currency=input_dto.currency,
            period=period.key,
            days_left=period.days_left,
            net_balance=balance.net_balance,
            accounts_count=balance.accounts_count,
            credit_cards_count=balance.credit_cards_count,
            month=MonthDTO(
                spent=month.expense_total,
                income=month.income_total,
                savings_rate=_savings_rate(month),
                movements=month.count,
            ),
            daily=DailyDTO(
                available=allowance.available,
                spent_today=today.expense_total,
                basis=allowance.basis,
            ),
            top_categories=_top_categories(month),
            recent=[RecentMovementDTO.from_view(view) for view in recent],
        )


def _savings_rate(month: PeriodSummary) -> float:
    """Share of the month's income still unspent. No income, no rate — not a zero
    that pretends to be a measurement."""
    if month.income_total <= 0:
        return 0.0
    return (month.income_total - month.expense_total) / month.income_total


def _top_categories(month: PeriodSummary) -> list[TopCategoryDTO]:
    """Biggest spenders of the month, weighted against the month's own spend.

    `share` is a portion of what was actually spent, not progress against a cap:
    there are no budgets yet, and inventing one would be the dishonest shortcut.
    """
    total = month.expense_total
    return [
        TopCategoryDTO(
            category_id=spend.category_id,
            spent=spend.spent,
            count=spend.count,
            share=(spend.spent / total) if total > 0 else 0.0,
        )
        for spend in month.by_category[:TOP_CATEGORIES]
    ]
