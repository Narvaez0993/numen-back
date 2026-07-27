from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.modules.subscriptions.domain.entities.subscription import SourceRef


@dataclass(frozen=True)
class RecordedExpense:
    """What the ledger answered: the movement that now exists."""

    movement_id: str


class ExpenseRecorder(Protocol):
    """Outbound port: turn a settled charge into a registered expense.

    The anti-corruption seam towards `movements`. This module decides **when** money
    moved; the movements module owns **how** (cash-basis, atomicity, idempotency), so
    a charge never touches a balance itself.

    `idempotency_key` is derived from the charge, so a retry of the same settlement
    returns the original movement instead of charging twice.
    """

    async def record(
        self,
        *,
        user_id: UUID,
        currency: str,
        description: str,
        amount: int,
        source: SourceRef,
        category_id: str | None,
        occurred_on: str,
        subscription_id: str,
        idempotency_key: str,
    ) -> RecordedExpense: ...
