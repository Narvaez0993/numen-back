"""Outbound port: turning a confirmed debt draft into a real debt.

The adapter calls debts' `CreateDebtUseCase` — the same door the manual flow uses,
so the person is resolved (or created) once, the loan transfer is recorded once, and
the account's balance really moves. Lending is not spending: the cash leaves as a
transfer, and the expense only ever appears if the debt is later written off.

`account_id` is deliberately optional all the way down: a dinner split moves no cash,
because the bill already left as one expense.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class RecordedDebt:
    debt_id: str


class DebtRecorder(Protocol):
    async def record(
        self,
        *,
        user_id: UUID,
        currency: str,
        today: str,
        direction: str,
        counterparty_id: str | None,
        counterparty_name: str | None,
        amount: int,
        account_id: str | None,
        due_on: str | None,
        note: str | None,
    ) -> RecordedDebt: ...
