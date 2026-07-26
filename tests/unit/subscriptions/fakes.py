from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID, uuid4

from src.modules.subscriptions.application.ports.charge_repository import (
    ChargeAlreadyOpenError,
)
from src.modules.subscriptions.application.ports.expense_recorder import RecordedExpense
from src.modules.subscriptions.application.ports.source_reader import SourceSnapshot
from src.modules.subscriptions.domain.entities.subscription import (
    Frequency,
    SourceRef,
    Subscription,
)
from src.modules.subscriptions.domain.entities.subscription_charge import (
    ChargeStatus,
    SubscriptionCharge,
)

T = TypeVar("T")

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


class FakeChargeRepository:
    """Rejects a duplicate `(user, subscription, due_on)` like the unique index does."""

    def __init__(self, charges: list[SubscriptionCharge] | None = None) -> None:
        self.charges = list(charges or [])

    async def open(self, charge: SubscriptionCharge) -> None:
        for existing in self.charges:
            if (
                existing.user_id == charge.user_id
                and existing.subscription_id == charge.subscription_id
                and existing.due_on == charge.due_on
            ):
                raise ChargeAlreadyOpenError(charge.subscription_id)
        self.charges.append(charge)

    async def save(self, charge: SubscriptionCharge) -> None:
        for index, existing in enumerate(self.charges):
            if existing.id == charge.id:
                self.charges[index] = charge
                return
        self.charges.append(charge)

    async def find(self, user_id: UUID, charge_id: str) -> SubscriptionCharge | None:
        for charge in self.charges:
            if charge.id == charge_id and charge.user_id == user_id:
                return charge
        return None

    async def list_by_status(
        self, user_id: UUID, status: str | None = None
    ) -> list[SubscriptionCharge]:
        return [
            c
            for c in self.charges
            if c.user_id == user_id and (status is None or c.status == status)
        ]

    async def list_pending_before(self, deadline: datetime) -> list[SubscriptionCharge]:
        return [c for c in self.charges if c.status == "pending" and c.opened_at <= deadline]


class FakeExpenseRecorder:
    """Stands in for the movements module; replays by idempotency key like it does."""

    def __init__(self) -> None:
        self.recorded: list[dict[str, object]] = []
        self._by_key: dict[str, str] = {}

    async def record(
        self,
        *,
        user_id: UUID,
        currency: str,
        description: str,
        amount: int,
        source: SourceRef,
        category_id: str | None,
        occurred_on: str,
        subscription_id: str,
        idempotency_key: str,
    ) -> RecordedExpense:
        if idempotency_key in self._by_key:
            return RecordedExpense(movement_id=self._by_key[idempotency_key])
        movement_id = f"mov-{len(self.recorded) + 1}"
        self._by_key[idempotency_key] = movement_id
        self.recorded.append(
            {
                "user_id": user_id,
                "description": description,
                "amount": amount,
                "source": source,
                "category_id": category_id,
                "occurred_on": occurred_on,
                "subscription_id": subscription_id,
                "idempotency_key": idempotency_key,
            }
        )
        return RecordedExpense(movement_id=movement_id)


class ImmediateUnitOfWork:
    """Runs the operation without a transaction — enough to assert the writes.

    Atomicity is a Mongo behaviour, verified end-to-end against docker.
    """

    def __init__(self) -> None:
        self.calls = 0

    async def atomic(self, operation: Callable[[], Awaitable[T]]) -> T:
        self.calls += 1
        return await operation()


def charge(
    *,
    user_id: UUID,
    subscription_id: str,
    due_on: str = TODAY,
    amount: int = 30_900,
    opened_at: datetime = FIXED_NOW,
    status: ChargeStatus = "pending",
) -> SubscriptionCharge:
    return SubscriptionCharge(
        id=str(uuid4()),
        user_id=user_id,
        subscription_id=subscription_id,
        due_on=due_on,
        amount=amount,
        currency=CURRENCY,
        status=status,
        opened_at=opened_at,
        settled_at=None,
        movement_id=None,
    )
