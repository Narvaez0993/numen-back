from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID


@dataclass(frozen=True)
class RecordedTransfer:
    movement_id: str


class TransferRecorder(Protocol):
    """Outbound port: the one way money enters or leaves a pocket.

    It records a **real transfer movement** through whoever owns movements — the
    account balance moves, the net balance moves, and the month's expenses and income
    do not (a transfer counts to neither, the existing cash-basis rule). Deleting the
    recorded movement reverts the money: undo comes free.
    """

    async def record(
        self,
        *,
        user_id: UUID,
        currency: str,
        description: str,
        amount: int,
        account_id: str,
        goal_id: str,
        direction: Literal["in", "out"],
        occurred_on: str,
    ) -> RecordedTransfer:
        """`in` = account → pocket (contribution) · `out` = pocket → account."""
        ...
