from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class DebtView:
    id: str
    direction: str
    """`i_owe` | `owed_to_me` (as debts names them)."""
    counterparty: str
    amount: int
    paid_total: int
    remaining: int
    status: str
    due_on: str | None


@dataclass(frozen=True)
class DebtsView:
    i_owe_total: int
    owed_to_me_total: int
    debts: tuple[DebtView, ...]


class DebtsReader(Protocol):
    async def snapshot(self, user_id: UUID, currency: str, today: str) -> DebtsView: ...
