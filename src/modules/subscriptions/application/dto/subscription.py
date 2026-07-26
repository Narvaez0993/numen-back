from pydantic import BaseModel

from src.modules.subscriptions.domain.entities.subscription import Subscription
from src.modules.subscriptions.domain.schedule import (
    monthly_equivalent,
    next_charge_on,
    yearly_equivalent,
)


class SubscriptionDTO(BaseModel):
    """A subscription as the client reads it. Amounts in the minor unit of `currency`.

    `next_charge_on` is **derived** from the schedule for the caller's `today`, not
    stored: nothing has to advance it, so it cannot go stale. `None` means paused.
    """

    id: str
    name: str
    amount: int
    currency: str
    frequency: str
    first_charge_on: str
    next_charge_on: str | None
    source_type: str
    source_id: str
    category_id: str | None
    icon: str
    color: str
    active: bool

    @classmethod
    def from_domain(cls, subscription: Subscription, today: str) -> "SubscriptionDTO":
        return cls(
            id=subscription.id,
            name=subscription.name,
            amount=subscription.amount,
            currency=subscription.currency,
            frequency=subscription.frequency,
            first_charge_on=subscription.first_charge_on,
            next_charge_on=next_charge_on(subscription, today),
            source_type=subscription.source.type,
            source_id=subscription.source.id,
            category_id=subscription.category_id,
            icon=subscription.icon,
            color=subscription.color,
            active=subscription.active,
        )


class SubscriptionsOverviewDTO(BaseModel):
    """The subscriptions screen in one read.

    `monthly` and `yearly` normalise every frequency (weekly 52/12, yearly /12) so
    the two totals mean the same thing for a gym paid weekly and a domain paid once
    a year. Paused subscriptions are listed but **excluded from the totals**: what
    you pay is what is running.
    """

    currency: str
    subscriptions: list[SubscriptionDTO]
    monthly: int
    yearly: int
    count: int

    @classmethod
    def build(
        cls, subscriptions: list[Subscription], *, currency: str, today: str
    ) -> "SubscriptionsOverviewDTO":
        active = [s for s in subscriptions if s.active]
        return cls(
            currency=currency,
            subscriptions=[SubscriptionDTO.from_domain(s, today) for s in subscriptions],
            monthly=sum(monthly_equivalent(s) for s in active),
            yearly=sum(yearly_equivalent(s) for s in active),
            count=len(active),
        )
