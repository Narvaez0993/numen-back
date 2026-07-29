from uuid import UUID

from pydantic import BaseModel


class CreateDebtInputDTO(BaseModel):
    """One-on-one. The person is an existing `counterparty_id` **or** a new
    `counterparty_name` (created inline); `currency` comes from the caller's
    preferences, never the body."""

    user_id: UUID
    currency: str
    today: str
    direction: str
    counterparty_id: str | None = None
    counterparty_name: str | None = None
    amount: int
    due_on: str | None = None
    note: str | None = None


class SplitInputDTO(BaseModel):
    counterparty_id: str | None = None
    counterparty_name: str | None = None
    amount: int


class CreateSharedEventInputDTO(BaseModel):
    """A split moment: the whole cost, and what each person owes of it. The user's own
    share is the rest — it is not a debt, so it is not sent."""

    user_id: UUID
    currency: str
    today: str
    direction: str
    name: str
    total: int
    due_on: str | None = None
    splits: list[SplitInputDTO]


class UpdateDebtInputDTO(BaseModel):
    """Partial patch: `None` means "leave this field untouched". The person and the
    direction are identity — changing who owes whom is another debt."""

    user_id: UUID
    debt_id: str
    today: str
    amount: int | None = None
    due_on: str | None = None
    clear_due_on: bool = False
    note: str | None = None
    clear_note: bool = False


class DeleteDebtInputDTO(BaseModel):
    user_id: UUID
    debt_id: str


class AddPaymentInputDTO(BaseModel):
    user_id: UUID
    debt_id: str
    today: str
    amount: int
    note: str | None = None


class RemovePaymentInputDTO(BaseModel):
    user_id: UUID
    debt_id: str
    payment_id: str
    today: str


class DebtsSnapshotInputDTO(BaseModel):
    user_id: UUID
    currency: str
    today: str


class DebtTotalsInputDTO(BaseModel):
    user_id: UUID
