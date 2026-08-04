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


@dataclass(frozen=True)
class GoalFunds:
    """What a goal's pocket holds: transfers in minus transfers out.

    There is no stored balance behind this — the pocket's money IS these movements,
    which is why it can never drift. `first_in_on` feeds the contribution-pace
    projection (goals owns that math; this is just the raw material).
    """

    goal_id: str
    saved: int
    first_in_on: str | None


@dataclass(frozen=True)
class DaySpend:
    """Expenses of one calendar day. Only days with movements appear —
    the reader decides whether an absent day means zero or "not yet"."""

    day: str
    spent: int
    count: int


@dataclass(frozen=True)
class MerchantSpend:
    """Expenses of a date range grouped by **what the user typed**.

    There is no merchant catalog: the description is free text, so "Exito", "exito "
    and "EXITO" are one merchant here (grouped case- and space-insensitively) and
    `label` carries the most recent spelling — the one the user last chose.
    """

    label: str
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

    async def spend_by_day(self, user_id: UUID, date_from: str, date_to: str) -> list[DaySpend]:
        """Expenses grouped by day, chronological. Days without spending are absent."""
        ...

    async def top_merchants(
        self,
        user_id: UUID,
        date_from: str,
        date_to: str,
        category_id: str | None,
        limit: int,
    ) -> list[MerchantSpend]:
        """Where the money of a category actually went, biggest first.

        `category_id=None` means the unclassified bucket, not "any category": it is a
        filter on the same field the listing uses.
        """
        ...

    async def top_merchants_overall(
        self, user_id: UUID, date_from: str, date_to: str, limit: int
    ) -> list[MerchantSpend]:
        """Where the period's money went, category-blind — the weekly review's
        biggest merchant. A separate question on purpose: overloading
        `category_id=None` above would silently rank only the unclassified
        bucket, which is exactly the bug this method exists to prevent."""
        ...

    async def goal_funds(self, user_id: UUID) -> list[GoalFunds]:
        """Per goal: transfers in minus out, and the day of the first contribution."""
        ...
