from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CategorySpendView:
    """`category_id is None` is the unclassified bucket."""

    category_id: str | None
    spent: int
    count: int


@dataclass(frozen=True)
class PeriodSummary:
    """Aggregated by the store, never by summing a list in memory."""

    expense_total: int = 0
    income_total: int = 0
    count: int = 0
    by_category: tuple[CategorySpendView, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RecentMovementView:
    """A movement as Home shows it: references only, no denormalized names.

    `overview` re-declares the shape it needs instead of importing the movements
    module — that is the anti-corruption seam, and it means renaming a category
    updates Home for free because the client resolves the label from its catalog.
    """

    id: str
    type: str
    description: str
    amount: int
    currency: str
    source_type: str
    source_id: str
    destination_type: str | None
    destination_id: str | None
    category_id: str | None
    occurred_on: str
    captured_via: str


class MovementSummaryReader(Protocol):
    """Outbound port: period aggregates and the latest movements."""

    async def summary(self, user_id: UUID, date_from: str, date_to: str) -> PeriodSummary:
        """A single day is just a range of one: `summary(u, today, today)`."""
        ...

    async def recent(self, user_id: UUID, limit: int) -> list[RecentMovementView]: ...
