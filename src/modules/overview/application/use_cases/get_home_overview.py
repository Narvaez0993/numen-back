from dataclasses import dataclass
from datetime import date, timedelta

from src.modules.overview.application.dto.home_overview import (
    BudgetDTO,
    HomeOverviewInputDTO,
    HomeOverviewOutputDTO,
    MonthDTO,
    PaceDTO,
    PreviousMonthDTO,
    RecentMovementDTO,
    TopCategoryDTO,
    UpcomingChargeDTO,
)
from src.modules.overview.application.ports.balance_reader import BalanceReader
from src.modules.overview.application.ports.budget_reader import BudgetReader
from src.modules.overview.application.ports.movement_summary_reader import (
    MovementSummaryReader,
    PeriodSummary,
)
from src.modules.overview.application.ports.upcoming_charges_reader import (
    UpcomingChargesReader,
)
from src.modules.overview.domain import hero_focus, spending_pace
from src.shared.domain.period import MonthPeriod

TOP_CATEGORIES = 4
RECENT_MOVEMENTS = 5
UPCOMING_CHARGES = 5
# A week ahead, not "the rest of the month": on the 31st the second window would be
# empty, and a charge landing on the 2nd is exactly what you want to know about.
UPCOMING_WINDOW_DAYS = 7


@dataclass
class GetHomeOverviewUseCase:
    """Composes the Home screen out of what the other modules already know.

    The only place in the backend that reads across modules, and it does it through its
    own ports — so Home can grow (budgets, goals) without any module learning about
    another.

    What it deliberately does **not** produce any more is a daily allowance. Dividing
    the month's leftover income by the days remaining answered "how much may I spend
    today", a permission this app has no business granting — and it rose whenever the
    user held back. Instead, `focus` picks the figure that serves what the user said
    they came for, and `pace` says where the month lands at their current rate.

    A daily figure is back in `budget`, and only there: it comes from a ceiling the user
    set, it is computed by the module that owns that ceiling, and it falls as they spend.
    """

    balance_reader: BalanceReader
    movement_summary_reader: MovementSummaryReader
    upcoming_charges_reader: UpcomingChargesReader
    budget_reader: BudgetReader

    async def execute(self, input_dto: HomeOverviewInputDTO) -> HomeOverviewOutputDTO:
        period = MonthPeriod.containing(date.fromisoformat(input_dto.today))
        previous_from, previous_to = period.same_span_last_month()

        balance = await self.balance_reader.read(input_dto.user_id, input_dto.currency)
        month = await self.movement_summary_reader.summary(
            input_dto.user_id, period.first_day, period.last_day
        )
        # A single day is a range of one; no special port method for it.
        today = await self.movement_summary_reader.summary(
            input_dto.user_id, input_dto.today, input_dto.today
        )
        previous = await self.movement_summary_reader.summary(
            input_dto.user_id, previous_from, previous_to
        )
        recent = await self.movement_summary_reader.recent(input_dto.user_id, RECENT_MOVEMENTS)
        cap = await self.budget_reader.global_cap(input_dto.user_id, input_dto.today)
        upcoming = await self.upcoming_charges_reader.upcoming(
            input_dto.user_id,
            input_dto.today,
            (
                date.fromisoformat(input_dto.today) + timedelta(days=UPCOMING_WINDOW_DAYS)
            ).isoformat(),
            UPCOMING_CHARGES,
        )

        pace = spending_pace.compute(
            spent=month.expense_total,
            days_elapsed=period.days_elapsed,
            total_days=period.total_days,
        )
        focus = hero_focus.choose(
            objective=input_dto.objective,
            has_movements=month.count > 0 or len(recent) > 0,
            card_debt=balance.card_debt,
            income=month.income_total,
            has_cap=cap is not None,
        )

        return HomeOverviewOutputDTO(
            currency=input_dto.currency,
            period=period.key,
            days_left=period.days_left,
            days_elapsed=period.days_elapsed,
            objective=input_dto.objective,
            focus=focus,
            net_balance=balance.net_balance,
            accounts_count=balance.accounts_count,
            credit_cards_count=balance.credit_cards_count,
            card_debt=balance.card_debt,
            card_limit=balance.card_limit,
            month=MonthDTO(
                spent=month.expense_total,
                income=month.income_total,
                saved=month.income_total - month.expense_total,
                savings_rate=_savings_rate(month),
                movements=month.count,
                spent_today=today.expense_total,
                previous=_previous(previous),
                change=spending_pace.change(month.expense_total, previous.expense_total),
            ),
            pace=(
                None
                if pace is None
                else PaceDTO(daily_average=pace.daily_average, projected=pace.projected)
            ),
            budget=None if cap is None else BudgetDTO.from_view(cap),
            top_categories=_top_categories(month),
            recent=[RecentMovementDTO.from_view(view) for view in recent],
            upcoming=[UpcomingChargeDTO.from_view(view) for view in upcoming],
        )


def _savings_rate(month: PeriodSummary) -> float:
    """Share of the month's income still unspent. No income, no rate — not a zero
    that pretends to be a measurement."""
    if month.income_total <= 0:
        return 0.0
    return (month.income_total - month.expense_total) / month.income_total


def _previous(previous: PeriodSummary) -> PreviousMonthDTO | None:
    """`None` on a first month: there is nothing to compare against, and a zero there
    would read as "you spent the same"."""
    if previous.count == 0:
        return None
    return PreviousMonthDTO(spent=previous.expense_total, income=previous.income_total)


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
