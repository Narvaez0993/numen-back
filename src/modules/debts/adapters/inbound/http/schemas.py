from pydantic import BaseModel, Field

from src.modules.debts.domain.entities.counterparty import MAX_NAME_LENGTH
from src.modules.debts.domain.entities.debt import MAX_NOTE_LENGTH
from src.modules.debts.domain.entities.shared_event import MAX_EVENT_NAME_LENGTH

# Amounts are integers in the minor unit of the user's currency, which the server
# owns: no request body carries a currency.


class CreateDebtRequest(BaseModel):
    """One-on-one. The person is an existing id or a new name (created inline)."""

    direction: str
    counterparty_id: str | None = None
    counterparty_name: str | None = Field(default=None, max_length=MAX_NAME_LENGTH)
    amount: int = Field(gt=0)
    account_id: str | None = None
    """The account the cash moved on, when it moved. Omit it for a debt that shifted
    no money — a dinner split, where the bill already left as one expense."""
    due_on: str | None = None
    note: str | None = Field(default=None, max_length=MAX_NOTE_LENGTH)


class SplitRequest(BaseModel):
    counterparty_id: str | None = None
    counterparty_name: str | None = Field(default=None, max_length=MAX_NAME_LENGTH)
    amount: int = Field(gt=0)


class CreateSharedEventRequest(BaseModel):
    """The dinner, split. `total` is the whole cost; the caller's own share is what
    the splits leave of it, so it is never sent."""

    direction: str
    name: str = Field(min_length=1, max_length=MAX_EVENT_NAME_LENGTH)
    total: int = Field(gt=0)
    due_on: str | None = None
    splits: list[SplitRequest]


class UpdateDebtRequest(BaseModel):
    """Absent keys keep their stored value; `due_on`/`note` sent as `null` clear.
    The person and the direction are identity and cannot change."""

    amount: int | None = Field(default=None, gt=0)
    due_on: str | None = None
    note: str | None = Field(default=None, max_length=MAX_NOTE_LENGTH)


class AddPaymentRequest(BaseModel):
    """A repayment moves real cash, so the account is required — unlike the loan,
    which may never have moved any."""

    amount: int = Field(gt=0)
    account_id: str = Field(min_length=1)
    note: str | None = Field(default=None, max_length=MAX_NOTE_LENGTH)


class PaymentResponse(BaseModel):
    id: str
    amount: int
    paid_on: str
    note: str | None


class DebtResponse(BaseModel):
    id: str
    direction: str
    """`incoming` = they owe me · `outgoing` = I owe them."""
    counterparty_id: str
    amount: int
    paid_total: int
    remaining: int
    """Derived for the caller's `today`, never stored — with `status`, the fields the
    client used to compute itself and now reads."""
    status: str
    due_on: str | None
    note: str | None
    event_id: str | None
    written_off_on: str | None
    """The day the user gave up on it, or nothing. What it cost is not here — that is
    the expense the write-off recorded, and it reads in Movimientos like any other."""
    payments: list[PaymentResponse]
    created_at: str


class CounterpartyResponse(BaseModel):
    id: str
    name: str
    color: str


class SharedEventResponse(BaseModel):
    id: str
    name: str
    total: int
    """What the whole thing cost, the caller's own share included — display only;
    what is still owed lives in the debts."""
    occurred_on: str


class DirectionTotalResponse(BaseModel):
    total: int
    count: int


class DebtsSnapshotResponse(BaseModel):
    currency: str
    today: str
    i_owe: DirectionTotalResponse
    """Live balances only: a paid debt is history, not money between you."""
    owed_to_me: DirectionTotalResponse
    counterparties: list[CounterpartyResponse]
    events: list[SharedEventResponse]
    debts: list[DebtResponse]
    """Paid ones included — the history sheet reads them; the client filters."""
