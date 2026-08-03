from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class SubscriptionView:
    id: str
    name: str
    amount: int
    frequency: str
    next_charge_on: str | None
    """`None` means paused."""


@dataclass(frozen=True)
class SubscriptionsView:
    monthly_total: int
    yearly_total: int
    subscriptions: tuple[SubscriptionView, ...]


@dataclass(frozen=True)
class UpcomingChargeView:
    subscription_id: str
    subscription_name: str
    amount: int
    due_on: str
    status: str
    """`pending` (due, awaiting an answer) or `scheduled`. Settled charges never
    appear here — they already live inside the month's expenses."""
    charge_id: str | None
    """Present only when `pending` — what confirm/skip act on."""


class SubscriptionsReader(Protocol):
    async def subscriptions(
        self, user_id: UUID, currency: str, today: str
    ) -> SubscriptionsView: ...

    async def upcoming_charges(
        self, user_id: UUID, currency: str, date_from: str, date_to: str, limit: int = 10
    ) -> tuple[UpcomingChargeView, ...]: ...
