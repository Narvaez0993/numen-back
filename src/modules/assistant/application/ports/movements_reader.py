from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CategorySpendView:
    category_id: str | None
    spent: int
    count: int


@dataclass(frozen=True)
class PeriodSummaryView:
    date_from: str
    date_to: str
    expense_total: int
    income_total: int
    count: int
    by_category: tuple[CategorySpendView, ...]


@dataclass(frozen=True)
class MovementView:
    id: str
    type: str
    description: str
    amount: int
    occurred_on: str
    category_id: str | None


@dataclass(frozen=True)
class MerchantView:
    label: str
    spent: int
    count: int


class MovementsReader(Protocol):
    """One port, three questions to the same source — like overview's reader."""

    async def summary(self, user_id: UUID, date_from: str, date_to: str) -> PeriodSummaryView: ...

    async def recent(self, user_id: UUID, limit: int) -> tuple[MovementView, ...]: ...

    async def top_merchants(
        self, user_id: UUID, date_from: str, date_to: str, limit: int
    ) -> tuple[MerchantView, ...]: ...
