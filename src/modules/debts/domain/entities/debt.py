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
class Debt:
    """Money between the user and a person: the **agreement**, and only that.

    What is owed lives here because it is a fact of the deal — plenty of debts never
    moved any cash at all, like a dinner split where the bill already left as one
    expense. What has been *paid* does not live here: repayments are the transfers
    that carried them, read back through `SettlementReader`. Storing both would let
    them disagree, and the prototype's persisted `balance` died of exactly that.

    Lending itself is not spending. Cash becomes a claim and the user is no poorer,
    so the money travels as a transfer between an account and this debt and the
    month's expenses do not move. An expense appears only when the debt is written
    off — the moment the loss is real.

    `written_off_on` is the one thing about that moment that IS stored, and on
    purpose: giving up is a decision about the agreement, like the due date, not a
    quantity that could drift. The money it costs stays derived — it is the expense
    movement the write-off recorded, and a claim that moved no cash (a dinner split)
    records none, because that loss was already paid when the bill was.

    `direction` reads from the user's side: `incoming` = they owe me, `outgoing` =
    I owe them. What is left (`remaining`, the status) is **derived** in `status.py`
    from the debt plus what came back.
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
    written_off_on: str | None = None
    """`YYYY-MM-DD` the user gave up on it, or nothing. Terminal: it beats every
    other status, because nothing is coming and the calendar stopped mattering."""
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
        # A fresh debt is never written off — you cannot give up on a deal you are
        # in the act of making.
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
            created_at=created_at,
        )

    def with_changes(self, **changes: object) -> "Debt":
        """A patched copy. Frozen on purpose: an edit produces a new value."""
        return replace(self, **changes)  # type: ignore[arg-type]
