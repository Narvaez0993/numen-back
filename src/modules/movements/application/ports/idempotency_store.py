from typing import Protocol
from uuid import UUID


class IdempotencyConflictError(Exception):
    """The key was taken by a concurrent request. Raised by `reserve`."""


class IdempotencyStore(Protocol):
    """Outbound port: remembers which movement a client's key already created.

    Guards the one write a double tap must never duplicate. `reserve` runs inside
    the same transaction as the movement, so a key never exists without its
    movement; a racing duplicate hits the uniqueness guard, aborts, and replays.
    Entries expire on their own after a day.
    """

    async def find(self, user_id: UUID, key: str) -> str | None: ...

    async def reserve(self, user_id: UUID, key: str, movement_id: str) -> None: ...
