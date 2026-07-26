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


@dataclass(frozen=True)
class MovementTotals:
    """What a date range added up to, by kind. Transfers are excluded from both
    totals: moving money between your own sources is neither spending nor earning."""

    expense_total: int = 0
    income_total: int = 0
    count: int = 0


@dataclass(frozen=True)
class CategorySpend:
    """Expenses of a date range grouped by category.

    `category_id is None` is the unclassified bucket — a real state worth showing
    (and what the assistant's rule-based insights will want to flag).
    """

    category_id: str | None
    spent: int
    count: int


class MovementRepository(Protocol):
    """Outbound port: persistence and aggregate reads of `Movement` (per user)."""

    async def search(self, query: MovementQuery) -> list[Movement]: ...

    async def find(self, user_id: UUID, movement_id: str) -> Movement | None: ...

    async def save(self, movement: Movement) -> None: ...

    async def delete(self, user_id: UUID, movement_id: str) -> None: ...

    async def totals(self, user_id: UUID, date_from: str, date_to: str) -> MovementTotals:
        """Sums the range **in the store**, not in memory: a month with 2.000
        movements must cost the same as one with 20."""
        ...

    async def spend_by_category(
        self, user_id: UUID, date_from: str, date_to: str
    ) -> list[CategorySpend]:
        """Expenses grouped by category, biggest first."""
        ...
