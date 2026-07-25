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
