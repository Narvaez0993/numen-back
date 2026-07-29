from pydantic import BaseModel

from src.modules.debts.domain import status as debt_status
from src.modules.debts.domain.entities.counterparty import Counterparty
from src.modules.debts.domain.entities.debt import Debt
from src.modules.debts.domain.entities.shared_event import SharedEvent


class PaymentDTO(BaseModel):
    id: str
    amount: int
    paid_on: str
    note: str | None


class DebtDTO(BaseModel):
    """A debt as the client reads it. `paid_total`, `remaining` and `status` are
    derived for the caller's `today` — never stored, so they cannot go stale."""

    id: str
    direction: str
    counterparty_id: str
    amount: int
    paid_total: int
    remaining: int
    status: str
    due_on: str | None
    note: str | None
    event_id: str | None
    payments: list[PaymentDTO]
    created_at: str

    @classmethod
    def from_domain(cls, debt: Debt, today: str) -> "DebtDTO":
        return cls(
            id=debt.id,
            direction=debt.direction,
            counterparty_id=debt.counterparty_id,
            amount=debt.amount,
            paid_total=debt_status.paid_total(debt),
            remaining=debt_status.remaining(debt),
            status=debt_status.status(debt, today),
            due_on=debt.due_on,
            note=debt.note,
            event_id=debt.event_id,
            payments=[
                PaymentDTO(id=p.id, amount=p.amount, paid_on=p.paid_on, note=p.note)
                for p in debt.payments
            ],
            created_at=debt.created_at.isoformat(),
        )


class CounterpartyDTO(BaseModel):
    id: str
    name: str
    color: str

    @classmethod
    def from_domain(cls, counterparty: Counterparty) -> "CounterpartyDTO":
        return cls(id=counterparty.id, name=counterparty.name, color=counterparty.color)


class SharedEventDTO(BaseModel):
    id: str
    name: str
    total: int
    occurred_on: str

    @classmethod
    def from_domain(cls, event: SharedEvent) -> "SharedEventDTO":
        return cls(id=event.id, name=event.name, total=event.total, occurred_on=event.occurred_on)


class DirectionTotalDTO(BaseModel):
    """What is still alive in one direction. Paid debts are history, not balance."""

    total: int
    count: int


class DebtTotalsDTO(BaseModel):
    """What Home asks for: live totals per direction, nothing else."""

    i_owe: int
    owed_to_me: int
    open_count: int


class DebtsSnapshotDTO(BaseModel):
    """The Deudas screen in one read.

    Paid debts travel too — the history sheet reads them — and the client filters:
    a user's debts are dozens, not thousands. Names and colours come embedded in
    `counterparties` because this module owns them; there is no external catalog to
    join against.
    """

    currency: str
    today: str
    i_owe: DirectionTotalDTO
    owed_to_me: DirectionTotalDTO
    counterparties: list[CounterpartyDTO]
    events: list[SharedEventDTO]
    debts: list[DebtDTO]
