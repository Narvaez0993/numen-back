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
    subscription_name: str
    amount: int
    due_on: str


class SubscriptionsReader(Protocol):
    async def subscriptions(
        self, user_id: UUID, currency: str, today: str
    ) -> SubscriptionsView: ...

    async def upcoming_charges(
        self, user_id: UUID, date_from: str, date_to: str
    ) -> tuple[UpcomingChargeView, ...]: ...
