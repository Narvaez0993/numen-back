from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.subscriptions.application.ports.source_reader import SourceSnapshot
from src.modules.subscriptions.domain.entities.subscription import (
    Frequency,
    SourceRef,
    Subscription,
)

FIXED_NOW = datetime(2026, 7, 26, 12, 0, 0, tzinfo=UTC)
TODAY = "2026-07-26"
CURRENCY = "COP"
ACCOUNT = SourceRef(type="account", id="nequi")
CARD = SourceRef(type="credit_card", id="visa")


class FixedClock:
    def __init__(self, now: datetime = FIXED_NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakeSubscriptionRepository:
    def __init__(self, subscriptions: list[Subscription] | None = None) -> None:
        self.subscriptions = list(subscriptions or [])

    async def list_by_user(self, user_id: UUID, *, only_active: bool = False) -> list[Subscription]:
        return [
            s for s in self.subscriptions if s.user_id == user_id and (s.active or not only_active)
        ]

    async def list_active(self) -> list[Subscription]:
        return [s for s in self.subscriptions if s.active]

    async def find(self, user_id: UUID, subscription_id: str) -> Subscription | None:
        for s in self.subscriptions:
            if s.id == subscription_id and s.user_id == user_id:
                return s
        return None

    async def save(self, subscription: Subscription) -> None:
        for index, existing in enumerate(self.subscriptions):
            if existing.id == subscription.id:
                self.subscriptions[index] = subscription
                return
        self.subscriptions.append(subscription)

    async def delete(self, user_id: UUID, subscription_id: str) -> bool:
        before = len(self.subscriptions)
        self.subscriptions = [
            s for s in self.subscriptions if not (s.id == subscription_id and s.user_id == user_id)
        ]
        return len(self.subscriptions) < before


class FakeSourceReader:
    """Knows the two sources of `fakes`; anything else does not exist."""

    def __init__(self, currency: str = CURRENCY, known: list[SourceRef] | None = None) -> None:
        self.currency = currency
        self.known = known if known is not None else [ACCOUNT, CARD]

    async def find(self, user_id: UUID, ref: SourceRef) -> SourceSnapshot | None:
        if ref not in self.known:
            return None
        return SourceSnapshot(ref=ref, currency=self.currency)


class FakeCategoryReader:
    def __init__(self, known: list[str] | None = None) -> None:
        self.known = known if known is not None else ["subs", "entretenimiento"]

    async def exists(self, user_id: UUID, category_id: str) -> bool:
        return category_id in self.known


def subscription(
    *,
    user_id: UUID | None = None,
    name: str = "Netflix",
    amount: int = 30_900,
    frequency: Frequency = "monthly",
    first_charge_on: str = "2026-07-28",
    source: SourceRef = ACCOUNT,
    category_id: str | None = "subs",
    active: bool = True,
    created_at: datetime = FIXED_NOW,
) -> Subscription:
    return Subscription(
        id=str(uuid4()),
        user_id=user_id or uuid4(),
        name=name,
        amount=amount,
        currency=CURRENCY,
        frequency=frequency,
        first_charge_on=first_charge_on,
        source=source,
        category_id=category_id,
        icon="device-tv",
        color="coral",
        active=active,
        created_at=created_at,
    )
