from pydantic import BaseModel

from src.modules.debts.application.ports.settlement_reader import DebtSettlement
from src.modules.debts.application.services import settlement as settlement_service
from src.modules.debts.domain import status as debt_status
from src.modules.debts.domain.entities.counterparty import Counterparty
from src.modules.debts.domain.entities.debt import Debt
from src.modules.debts.domain.entities.shared_event import SharedEvent


class PaymentDTO(BaseModel):
    """An instalment. Its `id` is the movement's: a repayment and the transfer that
    carried the money are one thing, so the client can open it in Movimientos."""

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
    written_off_on: str | None
    """The day the user gave up on it. What it cost is not here: it is the expense
    the write-off recorded, and it reads in Movimientos like any other."""
    payments: list[PaymentDTO]
    created_at: str

    @classmethod
    def from_domain(cls, debt: Debt, settlement: DebtSettlement, today: str) -> "DebtDTO":
        instalments = settlement_service.instalments(debt, settlement)
        repaid = sum(paid.amount for paid in instalments)
        return cls(
            id=debt.id,
            direction=debt.direction,
            counterparty_id=debt.counterparty_id,
            amount=debt.amount,
            paid_total=repaid,
            remaining=debt_status.remaining(debt, repaid),
            status=debt_status.status(debt, repaid, today),
            due_on=debt.due_on,
            note=debt.note,
            event_id=debt.event_id,
            written_off_on=debt.written_off_on,
            payments=[
                PaymentDTO(
                    id=repayment.movement_id,
                    amount=repayment.amount,
                    paid_on=repayment.occurred_on,
                    note=repayment.description or None,
                )
                for repayment in instalments
            ],
            created_at=debt.created_at.isoformat(),
        )


class AddPaymentOutputDTO(BaseModel):
    """The debt as it stands now, and the movement that just carried the money.

    Both, because they answer different questions: the screen redraws from the debt,
    and undo needs the movement — deleting it is what gives back the cash and reopens
    the balance in one act.
    """

    debt: DebtDTO
    movement_id: str


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
