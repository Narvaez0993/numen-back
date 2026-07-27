from typing import Protocol
from uuid import UUID

from src.modules.subscriptions.domain.entities.subscription import Subscription


class SubscriptionRepository(Protocol):
    """Outbound port for the subscriptions collection. Every read is tenant-scoped."""

    async def list_by_user(
        self, user_id: UUID, *, only_active: bool = False
    ) -> list[Subscription]: ...

    async def list_active(self) -> list[Subscription]:
        """Across every tenant — the charge opener runs for all users at once."""
        ...

    async def find(self, user_id: UUID, subscription_id: str) -> Subscription | None: ...

    async def save(self, subscription: Subscription) -> None: ...

    async def delete(self, user_id: UUID, subscription_id: str) -> bool: ...
