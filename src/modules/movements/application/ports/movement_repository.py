from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.modules.movements.domain.entities.movement import Movement, MovementType


@dataclass(frozen=True)
class MovementQuery:
    """Listing filters. Dates are inclusive `YYYY-MM-DD` bounds."""

    user_id: UUID
    date_from: str | None = None
    date_to: str | None = None
    type: MovementType | None = None
    source_id: str | None = None
    category_id: str | None = None
    limit: int = 100


class MovementRepository(Protocol):
    """Outbound port: persistence of `Movement` aggregates (per user)."""

    async def list(self, query: MovementQuery) -> list[Movement]: ...

    async def find(self, user_id: UUID, movement_id: str) -> Movement | None: ...

    async def save(self, movement: Movement) -> None: ...

    async def delete(self, user_id: UUID, movement_id: str) -> None: ...
