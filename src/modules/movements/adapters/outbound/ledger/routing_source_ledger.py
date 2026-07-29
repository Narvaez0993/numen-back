from dataclasses import dataclass
from uuid import UUID

from src.modules.movements.adapters.outbound.ledger.accounts_source_ledger import (
    AccountsSourceLedger,
)
from src.modules.movements.adapters.outbound.ledger.goals_pocket_ledger import (
    GoalsPocketLedger,
)
from src.modules.movements.application.ports.source_ledger import SourceSnapshot
from src.modules.movements.domain.entities.movement import SourceRef


@dataclass
class RoutingSourceLedger:
    """One `SourceLedger` over every kind of endpoint a movement can touch.

    Routes by the reference's type: accounts and cards to the accounts leg, pockets to
    the goals leg. The hexagon keeps seeing a single port — where the money actually
    sits is an adapter concern.
    """

    accounts: AccountsSourceLedger
    goals: GoalsPocketLedger

    def _leg(self, ref: SourceRef) -> AccountsSourceLedger | GoalsPocketLedger:
        return self.goals if ref.type == "goal" else self.accounts

    async def find(self, user_id: UUID, ref: SourceRef) -> SourceSnapshot | None:
        return await self._leg(ref).find(user_id, ref)

    async def apply_delta(self, user_id: UUID, ref: SourceRef, delta: int) -> None:
        await self._leg(ref).apply_delta(user_id, ref, delta)
