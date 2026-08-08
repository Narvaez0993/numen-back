from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID


@dataclass(frozen=True)
class RecordedTransfer:
    movement_id: str


class TransferRecorder(Protocol):
    """Outbound port: the one way cash crosses between an account and a debt.

    Lending is not spending. Handing a friend $5.000 turns cash into a claim: the
    account drops, the debt appears, and the user is no poorer for it — so this
    records a **real transfer movement**, which by the existing cash-basis rule
    counts toward neither the month's expenses nor its income. Getting repaid is the
    same move backwards.

    The expense in this story arrives exactly once, and later: when the debt is
    written off, because that is when the money is actually lost.

    Deleting the recorded movement reverts the cash, and — since what has been repaid
    is read back from these very movements — it reverts the debt's progress with it.
    Undo comes free and the two can never disagree.
    """

    async def record(
        self,
        *,
        user_id: UUID,
        currency: str,
        description: str,
        amount: int,
        account_id: str,
        debt_id: str,
        direction: Literal["out", "in"],
        occurred_on: str,
    ) -> RecordedTransfer:
        """`out` = account → debt (the money is lent, or handed over) ·
        `in` = debt → account (a repayment lands)."""
        ...

    async def record_loss(
        self,
        *,
        user_id: UUID,
        currency: str,
        description: str,
        amount: int,
        debt_id: str,
        occurred_on: str,
    ) -> RecordedTransfer:
        """The write-off: the claim given up, booked as an expense **out of the debt**.

        Out of the debt, not out of an account — the account was already debited the
        day the money was lent, and charging it twice would say the user paid the
        loss on top of making the loan. This is the one moment lending becomes
        spending, and it is the only expense the whole story ever produces.
        """
        ...

    async def revert(self, *, user_id: UUID, movement_id: str) -> bool:
        """Delete a transfer this port recorded, giving the account its money back
        and the debt its balance. `False` when there was nothing to delete — a
        repayment removed twice is not an error, it is already gone."""
        ...
