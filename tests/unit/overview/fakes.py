from uuid import UUID, uuid4

from src.modules.overview.application.ports.balance_reader import BalanceSnapshot
from src.modules.overview.application.ports.budget_reader import GlobalCapView
from src.modules.overview.application.ports.debt_reader import DebtTotalsView
from src.modules.overview.application.ports.goal_reader import TopGoalView
from src.modules.overview.application.ports.movement_summary_reader import (
    CategorySpendView,
    PeriodSummary,
    RecentMovementView,
)
from src.modules.overview.application.ports.upcoming_charges_reader import UpcomingChargeView

CURRENCY = "COP"
MONTH_KEY = "2026-07"


class FakeBalanceReader:
    def __init__(
        self,
        *,
        net_balance: int = 0,
        accounts_count: int = 0,
        credit_cards_count: int = 0,
        card_debt: int = 0,
        card_limit: int = 0,
    ) -> None:
        self.snapshot = BalanceSnapshot(
            net_balance=net_balance,
            accounts_count=accounts_count,
            credit_cards_count=credit_cards_count,
            card_debt=card_debt,
            card_limit=card_limit,
        )

    async def read(self, user_id: UUID, currency: str) -> BalanceSnapshot:
        return self.snapshot


class FakeMovementSummaryReader:
    """Answers per date range, so a test can set the month, today and last month apart.

    Dispatch is by the range itself rather than by call order: a single day is today, a
    range inside the current month is the month, anything else is the comparable stretch
    of the previous one.
    """

    def __init__(
        self,
        *,
        month: PeriodSummary | None = None,
        today: PeriodSummary | None = None,
        previous: PeriodSummary | None = None,
        recent: list[RecentMovementView] | None = None,
        month_key: str = MONTH_KEY,
    ) -> None:
        self.month = month or PeriodSummary()
        self.today = today or PeriodSummary()
        self.previous = previous or PeriodSummary()
        self.recent_movements = recent or []
        self.month_key = month_key
        self.ranges: list[tuple[str, str]] = []

    async def summary(self, user_id: UUID, date_from: str, date_to: str) -> PeriodSummary:
        self.ranges.append((date_from, date_to))
        if date_from == date_to:
            return self.today
        if date_from.startswith(self.month_key):
            return self.month
        return self.previous

    async def recent(self, user_id: UUID, limit: int) -> list[RecentMovementView]:
        return self.recent_movements[:limit]


class FakeUpcomingChargesReader:
    """Records the window it was asked about, so a test can assert it."""

    def __init__(self, charges: list[UpcomingChargeView] | None = None) -> None:
        self.charges = charges or []
        self.windows: list[tuple[str, str, int]] = []

    async def upcoming(
        self, user_id: UUID, date_from: str, date_to: str, limit: int
    ) -> list[UpcomingChargeView]:
        self.windows.append((date_from, date_to, limit))
        return self.charges[:limit]


class FakeBudgetReader:
    """No cap by default — most of Home's tests are about a user who never set one."""

    def __init__(self, cap: GlobalCapView | None = None) -> None:
        self.cap = cap
        self.days: list[str] = []

    async def global_cap(self, user_id: UUID, today: str) -> GlobalCapView | None:
        self.days.append(today)
        return self.cap


class FakeDebtReader:
    """Nobody owes anybody by default — most of Home's tests predate debts."""

    def __init__(self, totals: DebtTotalsView | None = None) -> None:
        self.result = totals or DebtTotalsView(i_owe=0, owed_to_me=0, open_count=0)

    async def totals(self, user_id: UUID) -> DebtTotalsView:
        return self.result


class FakeGoalReader:
    """No pocket by default — most of Home's tests predate goals."""

    def __init__(self, goal: TopGoalView | None = None) -> None:
        self.goal = goal

    async def top_goal(self, user_id: UUID, today: str) -> TopGoalView | None:
        return self.goal


def top_goal(
    *,
    name: str = "Viaje a Japón",
    target: int = 12_000_000,
    saved: int = 4_100_000,
    projected_on: str | None = "2027-04",
) -> TopGoalView:
    return TopGoalView(
        name=name,
        target=target,
        saved=saved,
        pct=saved / target,
        projected_on=projected_on,
    )


def debt_totals(*, i_owe: int = 0, owed_to_me: int = 0, open_count: int = 0) -> DebtTotalsView:
    return DebtTotalsView(i_owe=i_owe, owed_to_me=owed_to_me, open_count=open_count)


def global_cap(
    *,
    target: int = 3_000_000,
    spent: int = 1_919_500,
    per_day: int | None = 180_083,
    projected: int | None = 2_287_800,
    over: int | None = None,
) -> GlobalCapView:
    return GlobalCapView(
        target=target,
        spent=spent,
        remaining=target - spent,
        used=spent / target,
        per_day=per_day,
        projected=projected,
        over=over,
    )


def spend(category_id: str | None, amount: int, count: int = 1) -> CategorySpendView:
    return CategorySpendView(category_id=category_id, spent=amount, count=count)


def recent_movement(
    *, id: str = "mov-1", type: str = "expense", amount: int = 10_000
) -> RecentMovementView:
    return RecentMovementView(
        id=id,
        type=type,
        description="Café",
        amount=amount,
        currency=CURRENCY,
        source_type="account",
        source_id="nequi",
        destination_type=None,
        destination_id=None,
        category_id="cafe",
        occurred_on="2026-07-25",
        captured_via="manual",
        subscription_id=None,
    )


def upcoming_charge(
    *,
    subscription_id: str = "netflix",
    charge_on: str = "2026-07-28",
    amount: int = 30_900,
    status: str = "scheduled",
    charge_id: str | None = None,
) -> UpcomingChargeView:
    return UpcomingChargeView(
        subscription_id=subscription_id,
        charge_on=charge_on,
        amount=amount,
        status=status,
        charge_id=charge_id,
    )


def new_user_id() -> UUID:
    return uuid4()
