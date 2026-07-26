from uuid import UUID, uuid4

from src.modules.overview.application.ports.balance_reader import BalanceSnapshot
from src.modules.overview.application.ports.movement_summary_reader import (
    CategorySpendView,
    PeriodSummary,
    RecentMovementView,
)
from src.modules.overview.application.ports.upcoming_charges_reader import UpcomingChargeView

CURRENCY = "COP"


class FakeBalanceReader:
    def __init__(
        self,
        *,
        net_balance: int = 0,
        accounts_count: int = 0,
        credit_cards_count: int = 0,
    ) -> None:
        self.snapshot = BalanceSnapshot(
            net_balance=net_balance,
            accounts_count=accounts_count,
            credit_cards_count=credit_cards_count,
        )

    async def read(self, user_id: UUID, currency: str) -> BalanceSnapshot:
        return self.snapshot


class FakeMovementSummaryReader:
    """Answers per date range, so a test can set the month and today apart."""

    def __init__(
        self,
        *,
        month: PeriodSummary | None = None,
        today: PeriodSummary | None = None,
        recent: list[RecentMovementView] | None = None,
    ) -> None:
        self.month = month or PeriodSummary()
        self.today = today or PeriodSummary()
        self.recent_movements = recent or []
        self.ranges: list[tuple[str, str]] = []

    async def summary(self, user_id: UUID, date_from: str, date_to: str) -> PeriodSummary:
        self.ranges.append((date_from, date_to))
        return self.today if date_from == date_to else self.month

    async def recent(self, user_id: UUID, limit: int) -> list[RecentMovementView]:
        return self.recent_movements[:limit]


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


def new_user_id() -> UUID:
    return uuid4()


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
