from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

Direction = Literal["incoming", "outgoing"]

ALLOWED_DIRECTIONS: frozenset[str] = frozenset({"incoming", "outgoing"})
MAX_NOTE_LENGTH = 200
# Sanity bound for money in minor units, same as the rest of the app.
MAX_AMOUNT = 10**15


@dataclass(frozen=True)
class Payment:
    """A partial repayment. No account reference on purpose: a debt is a parallel
    ledger, so a payment marks progress on it and never moves a balance."""

    id: str
    amount: int
    paid_on: str
    note: str | None

    @classmethod
    def create(cls, *, amount: int, paid_on: str, note: str | None) -> "Payment":
        return cls(id=str(uuid4()), amount=amount, paid_on=paid_on, note=note)


@dataclass(frozen=True)
class Debt:
    """Money between the user and a person — a **record**, never a transaction.

    It does not create movements and does not touch balances: the month's spending is
    what left the user's pocket (cash-basis), and what a friend still owes them is not
    money they have — *"no estamos contando con plata que no tenemos"*. If the cash
    really moved, editing the account balance moves the anchor, which exists exactly
    for outside effects.

    `direction` reads from the user's side: `incoming` = they owe me, `outgoing` =
    I owe them. What is left (`paid_total`, `remaining`, the status) is **derived** in
    `status.py`, never persisted — the prototype stored a `balance` and that is the
    kind of field that goes stale.
    """

    id: str
    user_id: UUID
    direction: Direction
    counterparty_id: str
    amount: int
    """Positive, in the minor unit of `currency`."""
    currency: str
    due_on: str | None
    """`YYYY-MM-DD` or nothing. Never a display string — a stored "21 may" is the bug
    that broke `overdue` in the prototype."""
    note: str | None
    event_id: str | None
    """The shared event this debt was split from; `None` for a one-on-one debt."""
    payments: tuple[Payment, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        direction: Direction,
        counterparty_id: str,
        amount: int,
        currency: str,
        due_on: str | None,
        note: str | None,
        event_id: str | None,
        created_at: datetime,
    ) -> "Debt":
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            direction=direction,
            counterparty_id=counterparty_id,
            amount=amount,
            currency=currency,
            due_on=due_on,
            note=note,
            event_id=event_id,
            payments=(),
            created_at=created_at,
        )

    def with_payment(self, payment: Payment) -> "Debt":
        return replace(self, payments=(*self.payments, payment))

    def without_payment(self, payment_id: str) -> "Debt":
        return replace(self, payments=tuple(p for p in self.payments if p.id != payment_id))

    def with_changes(self, **changes: object) -> "Debt":
        """A patched copy. Frozen on purpose: an edit produces a new value."""
        return replace(self, **changes)  # type: ignore[arg-type]
