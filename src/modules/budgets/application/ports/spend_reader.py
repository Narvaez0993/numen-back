from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CategorySpendView:
    """`category_id is None` is the unclassified bucket."""

    category_id: str | None
    spent: int
    count: int


@dataclass(frozen=True)
class MerchantSpendView:
    """What the user typed, grouped: `label` is the most recent spelling."""

    label: str
    spent: int
    count: int


class SpendReader(Protocol):
    """Outbound port: what a period cost, read from wherever movements live.

    `budgets` declares the shape it needs instead of importing the movements module —
    the same anti-corruption seam `movements` uses for `SourceLedger`. The hexagon never
    learns that a movement has a source, a currency or an idempotency key; it only ever
    asks how much was spent.
    """

    async def spent(self, user_id: UUID, date_from: str, date_to: str) -> int:
        """Expenses of the range. Aggregated in the store, never by summing a list."""
        ...

    async def by_category(
        self, user_id: UUID, date_from: str, date_to: str
    ) -> list[CategorySpendView]: ...

    async def top_merchants(
        self,
        user_id: UUID,
        date_from: str,
        date_to: str,
        category_id: str | None,
        limit: int,
    ) -> list[MerchantSpendView]:
        """Where a category's money went, biggest first."""
        ...
