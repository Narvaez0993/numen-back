from dataclasses import dataclass
from uuid import UUID

from src.modules.subscriptions.application.ports.category_reader import CategoryReader
from src.modules.subscriptions.application.ports.source_reader import SourceReader
from src.modules.subscriptions.domain.entities.subscription import SourceRef
from src.modules.subscriptions.domain.errors import (
    InvalidSubscriptionError,
    SubscriptionCategoryNotFoundError,
    SubscriptionSourceNotFoundError,
)


@dataclass
class SubscriptionReferences:
    """Checks that what a subscription points at is real, is the caller's, and fits.

    Shared by create and update so both refuse exactly the same things — the same
    reason `movements` has `MovementReferences`.
    """

    source_reader: SourceReader
    category_reader: CategoryReader

    async def ensure_source(self, user_id: UUID, currency: str, ref: SourceRef) -> None:
        snapshot = await self.source_reader.find(user_id, ref)
        if snapshot is None:
            raise SubscriptionSourceNotFoundError(f"Source {ref.id} not found")
        if snapshot.currency != currency:
            raise InvalidSubscriptionError("Source currency does not match yours")

    async def ensure_category(self, user_id: UUID, category_id: str | None) -> None:
        if category_id is None:
            return
        if not await self.category_reader.exists(user_id, category_id):
            raise SubscriptionCategoryNotFoundError()
