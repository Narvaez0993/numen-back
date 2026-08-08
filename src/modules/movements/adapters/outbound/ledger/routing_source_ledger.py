from dataclasses import dataclass
from uuid import UUID

from src.modules.movements.adapters.outbound.ledger.accounts_source_ledger import (
    AccountsSourceLedger,
)
from src.modules.movements.adapters.outbound.ledger.debts_claim_ledger import (
    DebtsClaimLedger,
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
    the goals leg, claims to the debts leg. The hexagon keeps seeing a single port —
    where the money actually sits is an adapter concern.

    The routing is explicit rather than "goal here, everything else to accounts": that
    default silently sent a debt ref to the accounts leg, which looked for an account
    with a debt's id, found none, and answered "source not found" — a lie about what
    was wrong. A new endpoint kind should fail loudly here, not be mistaken for a
    missing account.
    """

    accounts: AccountsSourceLedger
    goals: GoalsPocketLedger
    debts: DebtsClaimLedger

    def _leg(self, ref: SourceRef) -> AccountsSourceLedger | GoalsPocketLedger | DebtsClaimLedger:
        if ref.type == "goal":
            return self.goals
        if ref.type == "debt":
            return self.debts
        return self.accounts

    async def find(self, user_id: UUID, ref: SourceRef) -> SourceSnapshot | None:
        return await self._leg(ref).find(user_id, ref)

    async def apply_delta(self, user_id: UUID, ref: SourceRef, delta: int) -> None:
        await self._leg(ref).apply_delta(user_id, ref, delta)
