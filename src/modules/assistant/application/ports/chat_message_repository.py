"""Outbound port: the single persistent thread per user.

Messages store their blocks as already-serialized dicts (the `LlmBlock` shape):
the thread is a log, not a place where money lives — drafts are referenced by id
and hydrated on read, so history always shows their current state.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class StoredChatMessage:
    id: str
    user_id: UUID
    role: str
    blocks: tuple[dict[str, Any], ...]
    client_message_id: str | None
    created_at: datetime


class ChatMessageRepository(Protocol):
    async def append(self, message: StoredChatMessage) -> None: ...

    async def recent(self, user_id: UUID, limit: int) -> tuple[StoredChatMessage, ...]:
        """The last `limit` messages in chronological order — the model window."""
        ...

    async def before(
        self, user_id: UUID, before_id: str | None, limit: int
    ) -> tuple[StoredChatMessage, ...]:
        """A page walking backwards from `before_id` (or the newest), chronological."""
        ...

    async def find_by_client_id(
        self, user_id: UUID, client_message_id: str
    ) -> StoredChatMessage | None: ...
