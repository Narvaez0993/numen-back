from pydantic import BaseModel, Field

from src.modules.subscriptions.domain.entities.subscription import MAX_NAME_LENGTH

# Amounts are integers in the minor unit of the user's currency, which the server
# owns: no request body carries a currency.


class CreateSubscriptionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    amount: int = Field(gt=0)
    frequency: str
    first_charge_on: str
    """The anchor date (`YYYY-MM-DD`). May be in the future (it starts next month)
    or in the past (you have paid it for a year) — no charge is ever opened for a
    date before the subscription existed."""
    source_type: str
    source_id: str
    category_id: str | None = None
    icon: str | None = None
    color: str | None = None


class UpdateSubscriptionRequest(BaseModel):
    """Absent keys keep their stored value. `active: false` pauses the charges."""

    name: str | None = Field(default=None, min_length=1, max_length=MAX_NAME_LENGTH)
    amount: int | None = Field(default=None, gt=0)
    frequency: str | None = None
    first_charge_on: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    category_id: str | None = None
    icon: str | None = None
    color: str | None = None
    active: bool | None = None


class SubscriptionResponse(BaseModel):
    id: str
    name: str
    amount: int
    currency: str
    frequency: str
    first_charge_on: str
    next_charge_on: str | None
    """Derived from the schedule for the caller's `today`; `null` when paused."""
    source_type: str
    source_id: str
    category_id: str | None
    icon: str
    color: str
    active: bool


class SubscriptionsOverviewResponse(BaseModel):
    currency: str
    subscriptions: list[SubscriptionResponse]
    monthly: int
    """Every frequency normalised to a month (weekly 52/12, yearly /12), paused ones
    excluded: what you pay is what is running."""
    yearly: int
    count: int
