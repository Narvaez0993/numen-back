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
    subscription_id: str | None


@dataclass(frozen=True)
class DaySpendView:
    """What one day cost."""

    day: str
    spent: int


class MovementSummaryReader(Protocol):
    """Outbound port: period aggregates, the month's rhythm, and the latest movements."""

    async def summary(self, user_id: UUID, date_from: str, date_to: str) -> PeriodSummary:
        """A single day is just a range of one: `summary(u, today, today)`."""
        ...

    async def recent(self, user_id: UUID, limit: int) -> list[RecentMovementView]: ...

    async def spend_by_day(
        self, user_id: UUID, date_from: str, date_to: str
    ) -> tuple[DaySpendView, ...]:
        """Every day in the range, **including the ones that cost nothing**.

        The store only knows about days that had movements, but Home draws this as a
        row of bars where position IS the date — a sparse answer would slide every
        bar after a quiet day onto the wrong one. Densifying is the reader's job
        because it is Home's requirement, not the ledger's.
        """
        ...
