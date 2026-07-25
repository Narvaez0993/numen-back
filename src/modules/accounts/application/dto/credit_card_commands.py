from uuid import UUID

from pydantic import BaseModel


class CreateCreditCardInputDTO(BaseModel):
    user_id: UUID
    tier: str
    currency: str
    name: str
    icon: str = ""
    color: str = ""
    debt: int = 0
    limit: int
    cutoff_day: int
    due_day: int | None = None


class UpdateCreditCardInputDTO(BaseModel):
    """Partial update: `None` means "leave this field untouched"."""

    user_id: UUID
    card_id: str
    name: str | None = None
    icon: str | None = None
    color: str | None = None
    debt: int | None = None
    limit: int | None = None
    cutoff_day: int | None = None
    due_day: int | None = None


class DeleteCreditCardInputDTO(BaseModel):
    user_id: UUID
    card_id: str
