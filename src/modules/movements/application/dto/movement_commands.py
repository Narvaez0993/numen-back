from uuid import UUID

from pydantic import BaseModel


class CreateMovementInputDTO(BaseModel):
    """`currency` comes from the caller's preferences, never from the request body."""

    user_id: UUID
    currency: str
    type: str
    description: str
    amount: int
    source_type: str
    source_id: str
    destination_type: str | None = None
    destination_id: str | None = None
    category_id: str | None = None
    occurred_on: str
    captured_via: str = "manual"
    idempotency_key: str | None = None


class UpdateMovementInputDTO(BaseModel):
    """Partial patch: `None` means "leave this field untouched".

    `type` is absent on purpose — turning an expense into a transfer changes the
    whole shape, so it is a different movement, not an edit.
    """

    user_id: UUID
    movement_id: str
    description: str | None = None
    amount: int | None = None
    source_type: str | None = None
    source_id: str | None = None
    destination_type: str | None = None
    destination_id: str | None = None
    category_id: str | None = None
    occurred_on: str | None = None


class DeleteMovementInputDTO(BaseModel):
    user_id: UUID
    movement_id: str
