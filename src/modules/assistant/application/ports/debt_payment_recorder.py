"""Outbound port: turning a confirmed payment draft into a real repayment.

The adapter calls debts' `AddPaymentUseCase` — the same door the Deudas screen uses,
so the transfer that carries the money is recorded once and what has been repaid stays
derived from it. Nothing is written onto the debt, which is why deleting the movement
later gives back both the cash and the balance.

The account is required, unlike a loan's: money always changes hands when a debt is
paid down. There is no honest "no money moved" answer to a repayment.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class RecordedPayment:
    movement_id: str
    """The transfer that carried the money. Undo is deleting exactly this."""


class DebtPaymentRecorder(Protocol):
    async def record(
        self,
        *,
        user_id: UUID,
        today: str,
        debt_id: str,
        amount: int,
        account_id: str,
        note: str | None,
    ) -> RecordedPayment: ...
