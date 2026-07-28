from typing import Literal

from pydantic import BaseModel, Field

# `amount` is a positive integer in the minor unit of the user's currency; the sign
# is a consequence of `type`. `occurred_on` is a date (`YYYY-MM-DD`), not a instant.

# What a request may point at. The domain also knows `goal`, but pocket transfers are
# minted only by the goals module through its port — never from this form.
RequestSourceType = Literal["account", "credit_card"]


class MovementResponse(BaseModel):
    id: str
    type: str
    description: str
    amount: int
    currency: str
    source_type: str
    source_id: str
    destination_type: str | None
    destination_id: str | None
    category_id: str | None
    occurred_on: str
    captured_via: str
    subscription_id: str | None = None
    """Present when a subscription's charge produced it — that is what makes the
    client show the "recurring" badge. Read-only: it is not part of any request."""


class MovementsListResponse(BaseModel):
    movements: list[MovementResponse]


class CreateMovementRequest(BaseModel):
    type: str
    description: str = Field(min_length=1, max_length=80)
    amount: int
    source_type: RequestSourceType
    source_id: str = Field(min_length=1, max_length=64)
    destination_type: str | None = None
    destination_id: str | None = Field(default=None, max_length=64)
    category_id: str | None = Field(default=None, max_length=64)
    # Only a length guard here: the domain owns the "is this a real day" rule and
    # answers with a message that says what it expected.
    occurred_on: str = Field(min_length=1, max_length=10)
    captured_via: str = "manual"


class UpdateMovementRequest(BaseModel):
    """Everything optional: absent fields keep their stored value. `type` cannot
    change (see `UpdateMovementInputDTO`)."""

    description: str | None = Field(default=None, min_length=1, max_length=80)
    amount: int | None = None
    source_type: RequestSourceType | None = None
    source_id: str | None = Field(default=None, min_length=1, max_length=64)
    destination_type: str | None = None
    destination_id: str | None = Field(default=None, min_length=1, max_length=64)
    category_id: str | None = Field(default=None, max_length=64)
    occurred_on: str | None = Field(default=None, min_length=1, max_length=10)


class CategorySpendResponse(BaseModel):
    """`category_id: null` is the unclassified bucket."""

    category_id: str | None
    spent: int
    count: int


class MovementSummaryResponse(BaseModel):
    date_from: str
    date_to: str
    expense_total: int
    income_total: int
    count: int
    by_category: list[CategorySpendResponse]
