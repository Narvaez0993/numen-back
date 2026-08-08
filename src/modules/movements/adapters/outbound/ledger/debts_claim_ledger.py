from dataclasses import dataclass
from uuid import UUID

from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.movements.application.ports.source_ledger import SourceSnapshot
from src.modules.movements.domain.entities.movement import SourceRef


@dataclass
class DebtsClaimLedger:
    """The `debt` leg of the source ledger.

    `find` resolves a claim the way accounts resolve theirs (exists, is the caller's,
    carries its currency) — through debts' port, never its documents.

    `apply_delta` is deliberately a **no-op**, for the same reason a pocket's is: a
    debt has no stored balance to move. What has been lent and repaid IS the sum of
    these very movements, recomputed on every read, so there is nothing to increment
    and nothing that can drift. The account on the other end of the transfer still
    gets its real `$inc` from the accounts leg — which is the whole point: lending
    drops your balance without touching the month's expenses.
    """

    debt_repository: DebtRepository

    async def find(self, user_id: UUID, ref: SourceRef) -> SourceSnapshot | None:
        debt = await self.debt_repository.find(user_id, ref.id)
        if debt is None:
            return None
        return SourceSnapshot(ref=ref, type="debt", currency=debt.currency)

    async def apply_delta(self, user_id: UUID, ref: SourceRef, delta: int) -> None:
        return None
