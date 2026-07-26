from dataclasses import dataclass
from uuid import UUID

from src.modules.movements.application.ports.category_lookup import CategoryLookup
from src.modules.movements.application.ports.source_ledger import SourceLedger
from src.modules.movements.domain.entities.movement import MovementType, SourceRef
from src.modules.movements.domain.errors import (
    MovementCategoryNotFoundError,
    SourceCurrencyMismatchError,
    SourceNotFoundError,
)


@dataclass
class MovementReferences:
    """Checks that what a movement points at is real, is the caller's, and fits.

    Shared by create and update so both refuse exactly the same things — the rules
    live here once instead of drifting apart in two use cases.
    """

    source_ledger: SourceLedger
    category_lookup: CategoryLookup

    async def ensure_source(self, user_id: UUID, currency: str, ref: SourceRef) -> None:
        snapshot = await self.source_ledger.find(user_id, ref)
        if snapshot is None:
            raise SourceNotFoundError(f"Source {ref.id} not found")
        if snapshot.currency != currency:
            raise SourceCurrencyMismatchError(snapshot.currency, currency)

    async def ensure_sources(
        self, user_id: UUID, currency: str, source: SourceRef, destination: SourceRef | None
    ) -> None:
        await self.ensure_source(user_id, currency, source)
        if destination is not None:
            await self.ensure_source(user_id, currency, destination)

    async def ensure_category(
        self, user_id: UUID, category_id: str | None, movement_type: MovementType
    ) -> None:
        """A category belongs to a flow: a salary is not a way to spend."""
        if category_id is None:
            return
        flow = "income" if movement_type == "income" else "expense"
        if not await self.category_lookup.exists(user_id, category_id, flow):
            raise MovementCategoryNotFoundError()
