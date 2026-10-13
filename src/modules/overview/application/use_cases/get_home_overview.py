from dataclasses import dataclass
from datetime import date, timedelta

from src.modules.overview.application.dto.home_overview import (
    BudgetDTO,
    DaySpendDTO,
    DebtsDTO,
    GoalDTO,
    HomeOverviewInputDTO,
    HomeOverviewOutputDTO,
    MonthDTO,
    PaceDTO,
    PreviousMonthDTO,
    RecentMovementDTO,
    TopCategoryCapDTO,
    TopCategoryDTO,
    UpcomingChargeDTO,
)
from src.modules.overview.application.ports.balance_reader import BalanceReader
from src.modules.overview.application.ports.budget_reader import BudgetReader, CategoryCapView
from src.modules.overview.application.ports.debt_reader import DebtReader
from src.modules.overview.application.ports.goal_reader import GoalReader
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
    debt_reader: DebtReader
    goal_reader: GoalReader

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
        # First of the month to today, not to the last day: the strip is what has
        # happened, and trailing zeros for days that have not arrived would read as
        # days the user spent nothing.
        by_day = await self.movement_summary_reader.spend_by_day(
            input_dto.user_id, period.first_day, input_dto.today
        )
        cap = await self.budget_reader.global_cap(input_dto.user_id, input_dto.today)
        category_caps = await self.budget_reader.category_caps(input_dto.user_id, input_dto.today)
        debts = await self.debt_reader.totals(input_dto.user_id)
        goal = await self.goal_reader.top_goal(input_dto.user_id, input_dto.today)
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
            personal_debt=debts.i_owe,
            income=month.income_total,
            has_cap=cap is not None,
            has_goal=goal is not None,
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
            debts=DebtsDTO.from_view(debts),
            goal=None if goal is None else GoalDTO.from_view(goal),
            top_categories=_top_categories(month, category_caps),
            recent=[RecentMovementDTO.from_view(view) for view in recent],
            upcoming=[UpcomingChargeDTO.from_view(view) for view in upcoming],
            by_day=[DaySpendDTO.from_view(view) for view in by_day],
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


def _top_categories(month: PeriodSummary, caps: dict[str, CategoryCapView]) -> list[TopCategoryDTO]:
    """Biggest spenders of the month, each against the best yardstick it has.

    A watched category travels with its `cap`, so Home measures it exactly as the
    Presupuestos screen does. Only the ones nobody put a limit on fall back to `share` of
    the month's spend — and they say so, because a bar that fills up has to mean the same
    thing on every screen of this app. It used to mean two things here: a category that
    took every peso of the month showed a full bar while its cap sat at 40% spent, which
    read as a cap blown that was not.

    Inventing a cap is still the dishonest shortcut; **using the one the user set** is
    what became possible.
    """
    total = month.expense_total
    return [
        TopCategoryDTO(
            category_id=spend.category_id,
            spent=spend.spent,
            count=spend.count,
            share=(spend.spent / total) if total > 0 else 0.0,
            cap=_cap(spend.category_id, caps),
        )
        for spend in month.by_category[:TOP_CATEGORIES]
    ]


def _cap(category_id: str | None, caps: dict[str, CategoryCapView]) -> TopCategoryCapDTO | None:
    """The unclassified bucket has no id, and therefore never a cap."""
    if category_id is None:
        return None
    cap = caps.get(category_id)
    return None if cap is None else TopCategoryCapDTO(target=cap.target, used=cap.used)
