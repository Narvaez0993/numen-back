from dataclasses import dataclass
from uuid import UUID

from src.modules.goals.application.ports.goal_repository import GoalRepository
from src.modules.movements.application.ports.source_ledger import SourceSnapshot
from src.modules.movements.domain.entities.movement import SourceRef


@dataclass
class GoalsPocketLedger:
    """The `goal` leg of the source ledger.

    `find` resolves a pocket the way accounts resolve theirs (exists, is the caller's,
    carries its currency) — through goals' port, never its documents.

    `apply_delta` is deliberately a **no-op**: a pocket has no stored balance to move.
    Its money IS the sum of its transfer movements, recomputed on every read, so there
    is nothing to increment and nothing that can drift. The account on the other end
    of the transfer still gets its real `$inc` from the accounts leg.
    """

    goal_repository: GoalRepository

    async def find(self, user_id: UUID, ref: SourceRef) -> SourceSnapshot | None:
        goal = await self.goal_repository.find(user_id, ref.id)
        if goal is None:
            return None
        return SourceSnapshot(ref=ref, type="goal", currency=goal.currency)

    async def apply_delta(self, user_id: UUID, ref: SourceRef, delta: int) -> None:
        return None
