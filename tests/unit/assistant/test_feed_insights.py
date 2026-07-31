"""Rule insights: computed on read, filtered by dismissals, zero LLM."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import pytest

from src.modules.assistant.application.ports.budgets_reader import (
    BudgetsView,
    CapView,
    CategoryCapView,
)
from src.modules.assistant.application.ports.movements_reader import (
    CategorySpendView,
    MerchantView,
    MovementView,
    PeriodSummaryView,
)
from src.modules.assistant.application.ports.subscriptions_reader import (
    SubscriptionsView,
    UpcomingChargeView,
)
from src.modules.assistant.application.use_cases.get_feed import (
    FeedInputDTO,
    GetAssistantFeedUseCase,
)

from .fakes import CURRENCY, TODAY, USER_ID, FakeCategoriesReader


def cap(id: str = "b-1", target: int = 100, spent: int = 85, over: int | None = None) -> CapView:
    return CapView(
        id=id,
        target=target,
        spent=spent,
        remaining=target - spent,
        per_day=None,
        projected=None,
        over=over,
        used=spent / target,
    )


def category_cap(
    category_id: str = "comida", spent: int = 90, target: int = 100, over: int | None = None
) -> CategoryCapView:
    return CategoryCapView(
        id=f"b-{category_id}",
        category_id=category_id,
        target=target,
        spent=spent,
        remaining=target - spent,
        over=over,
        used=spent / target,
    )


class StubBudgets:
    def __init__(self, view: BudgetsView) -> None:
        self.view = view

    async def snapshot(self, user_id: UUID, currency: str, today: str) -> BudgetsView:
        return self.view


class StubSubscriptions:
    def __init__(self, charges: tuple[UpcomingChargeView, ...] = ()) -> None:
        self.charges = charges
        self.calls: list[tuple[str, str, int]] = []

    async def subscriptions(self, user_id: UUID, currency: str, today: str) -> SubscriptionsView:
        return SubscriptionsView(monthly_total=0, yearly_total=0, subscriptions=())

    async def upcoming_charges(
        self, user_id: UUID, currency: str, date_from: str, date_to: str, limit: int = 10
    ) -> tuple[UpcomingChargeView, ...]:
        self.calls.append((date_from, date_to, limit))
        return self.charges


class StubMovements:
    def __init__(self, by_category: tuple[CategorySpendView, ...] = ()) -> None:
        self.by_category = by_category

    async def summary(self, user_id: UUID, date_from: str, date_to: str) -> PeriodSummaryView:
        return PeriodSummaryView(
            date_from=date_from,
            date_to=date_to,
            expense_total=0,
            income_total=0,
            count=0,
            by_category=self.by_category,
        )

    async def recent(self, user_id: UUID, limit: int) -> tuple[MovementView, ...]:
        return ()

    async def top_merchants(
        self, user_id: UUID, date_from: str, date_to: str, limit: int
    ) -> tuple[MerchantView, ...]:
        return ()


class FakeDismissals:
    def __init__(self, dismissed: set[str] | None = None) -> None:
        self.dismissed = dismissed or set()
        self.recorded: list[str] = []

    async def dismiss(self, user_id: UUID, key: str, at: datetime) -> None:
        self.recorded.append(key)
        self.dismissed.add(key)

    async def dismissed_among(self, user_id: UUID, keys: Sequence[str]) -> frozenset[str]:
        return frozenset(k for k in keys if k in self.dismissed)


def use_case(
    *,
    budgets: BudgetsView | None = None,
    charges: tuple[UpcomingChargeView, ...] = (),
    by_category: tuple[CategorySpendView, ...] = (),
    dismissed: set[str] | None = None,
) -> tuple[GetAssistantFeedUseCase, StubSubscriptions]:
    subs = StubSubscriptions(charges)
    case = GetAssistantFeedUseCase(
        budgets_reader=StubBudgets(
            budgets or BudgetsView(period=TODAY[:7], days_left=4, month=None, categories=())
        ),
        subscriptions_reader=subs,
        movements_reader=StubMovements(by_category),
        categories_reader=FakeCategoriesReader(),
        dismissals=FakeDismissals(dismissed),
    )
    return case, subs


def feed_input() -> FeedInputDTO:
    return FeedInputDTO(user_id=USER_ID, currency=CURRENCY, today=TODAY)


@pytest.mark.asyncio
async def test_a_cap_at_80_percent_alerts_and_a_low_one_does_not() -> None:
    view = BudgetsView(
        period="2026-07",
        days_left=4,
        month=cap(spent=85),
        categories=(category_cap("comida", spent=90), category_cap("hogar", spent=10)),
    )
    case, _ = use_case(budgets=view)

    feed = await case.execute(feed_input())

    keys = [i.key for i in feed.insights]
    assert "cap:global:2026-07" in keys
    assert "cap:comida:2026-07" in keys
    assert all("hogar" not in k for k in keys)
    comida = next(i for i in feed.insights if i.key == "cap:comida:2026-07")
    assert comida.kind == "cap_alert"
    assert comida.category_name == "Comida"  # resolved, not an id


@pytest.mark.asyncio
async def test_a_broken_cap_alerts_even_past_100_percent() -> None:
    view = BudgetsView(
        period="2026-07",
        days_left=4,
        month=None,
        categories=(category_cap("comida", spent=130, over=30),),
    )
    case, _ = use_case(budgets=view)

    feed = await case.execute(feed_input())

    assert feed.insights[0].used > 1
    assert feed.insights[0].over == 30


@pytest.mark.asyncio
async def test_upcoming_charges_look_two_days_ahead() -> None:
    charge = UpcomingChargeView(
        subscription_id="sub-1",
        subscription_name="Netflix",
        amount=30_000,
        due_on="2026-07-29",
        status="pending",
        charge_id="ch-1",
    )
    case, subs = use_case(charges=(charge,))

    feed = await case.execute(feed_input())

    assert subs.calls == [(TODAY, "2026-07-30", 10)]
    insight = feed.insights[0]
    assert insight.kind == "upcoming_charge"
    assert insight.key == "charge:ch-1"
    assert insight.name == "Netflix"


@pytest.mark.asyncio
async def test_a_scheduled_charge_keys_by_subscription_and_date() -> None:
    charge = UpcomingChargeView(
        subscription_id="sub-1",
        subscription_name="Gym",
        amount=80_000,
        due_on="2026-07-30",
        status="scheduled",
        charge_id=None,
    )
    case, _ = use_case(charges=(charge,))

    feed = await case.execute(feed_input())

    assert feed.insights[0].key == "charge:sub-1:2026-07-30"


@pytest.mark.asyncio
async def test_three_uncategorized_movements_trigger_the_sweep_hint() -> None:
    case, _ = use_case(by_category=(CategorySpendView(category_id=None, spent=90_000, count=3),))

    feed = await case.execute(feed_input())

    assert feed.insights[0].kind == "uncategorized"
    assert feed.insights[0].key == "uncat:2026-07"
    assert feed.insights[0].count == 3


@pytest.mark.asyncio
async def test_two_uncategorized_are_not_worth_a_card() -> None:
    case, _ = use_case(by_category=(CategorySpendView(category_id=None, spent=50_000, count=2),))

    feed = await case.execute(feed_input())

    assert feed.insights == []


@pytest.mark.asyncio
async def test_dismissed_insights_stay_gone() -> None:
    view = BudgetsView(period="2026-07", days_left=4, month=cap(spent=90), categories=())
    case, _ = use_case(budgets=view, dismissed={"cap:global:2026-07"})

    feed = await case.execute(feed_input())

    assert feed.insights == []
