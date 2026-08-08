from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class DebtMovement:
    """One movement that touched this debt.

    Its `movement_id` is the whole identity: an instalment and the movement that
    carried it are the same thing, so the client can open it in Movimientos and
    deleting it there undoes the instalment.

    `is_loss` marks the write-off — an expense out of the claim, not cash anyone paid
    back. It leaves the debt like a repayment does and means the opposite, so the two
    must never be summed together.
    """

    movement_id: str
    amount: int
    occurred_on: str
    description: str
    is_loss: bool = False


@dataclass(frozen=True)
class DebtSettlement:
    """Every transfer touching one debt, split by which way the money went.

    Deliberately NOT split into "principal" and "repayment": the same direction means
    opposite things depending on which way the debt runs. Money leaving my account
    into a debt is a loan when they owe me, and a repayment when I owe them. Only the
    debt knows, so the reader reports the flows and `settlement.py` reads them against
    the direction.
    """

    debt_id: str
    into_debt: tuple[DebtMovement, ...]
    """Movements whose destination was the debt — money leaving the user's accounts."""
    out_of_debt: tuple[DebtMovement, ...]
    """Movements whose source was the debt: money landing in an account, or — when
    `is_loss` — the claim written off, which lands nowhere."""


NO_SETTLEMENT = DebtSettlement(debt_id="", into_debt=(), out_of_debt=())
"""A debt no cash has ever crossed. Handy for the common `.get(id, …)` read — and the
honest default, since a dinner split never moves any."""


class SettlementReader(Protocol):
    """Outbound port: a debt's cash history, read from wherever movements live.

    `debts` declares the shape it needs instead of importing the movements module —
    the same anti-corruption seam every other module uses.

    Instalments are **not stored on the debt**. They are these transfers, so the two
    cannot drift: deleting the movement in Movimientos gives the account its money
    back and the debt its balance back, in one act, with nothing left to reconcile.
    The prototype's stored `balance` died for exactly this reason.
    """

    async def settlements(self, user_id: UUID) -> dict[str, DebtSettlement]: ...
