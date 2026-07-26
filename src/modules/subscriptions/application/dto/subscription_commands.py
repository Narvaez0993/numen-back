from uuid import UUID

from pydantic import BaseModel


class CreateSubscriptionInputDTO(BaseModel):
    """`currency` comes from the caller's preferences, never from the request body."""

    user_id: UUID
    currency: str
    today: str
    name: str
    amount: int
    frequency: str
    first_charge_on: str
    source_type: str
    source_id: str
    category_id: str | None = None
    icon: str | None = None
    color: str | None = None


class UpdateSubscriptionInputDTO(BaseModel):
    """Partial patch: `None` means "leave this field untouched".

    `active` is here because pausing is an edit, not a deletion — it stops the
    charges from opening while keeping the subscription and its history.
    """

    user_id: UUID
    currency: str
    today: str
    subscription_id: str
    name: str | None = None
    amount: int | None = None
    frequency: str | None = None
    first_charge_on: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    category_id: str | None = None
    icon: str | None = None
    color: str | None = None
    active: bool | None = None


class DeleteSubscriptionInputDTO(BaseModel):
    user_id: UUID
    subscription_id: str


class ListSubscriptionsInputDTO(BaseModel):
    user_id: UUID
    currency: str
    today: str
