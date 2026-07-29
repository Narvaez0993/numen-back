from typing import Protocol
from uuid import UUID

from src.modules.debts.domain.entities.shared_event import SharedEvent


class EventRepository(Protocol):
    """Outbound port: the split moments that group debts (per user)."""

    async def list_by_user(self, user_id: UUID) -> list[SharedEvent]: ...

    async def find(self, user_id: UUID, event_id: str) -> SharedEvent | None: ...

    async def save(self, event: SharedEvent) -> None: ...

    async def delete(self, user_id: UUID, event_id: str) -> None: ...
