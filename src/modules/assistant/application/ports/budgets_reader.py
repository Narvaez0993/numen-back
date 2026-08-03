from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CapView:
    id: str
    """The budget's id — what a "raise this cap" play needs to execute."""
    target: int
    spent: int
    remaining: int
    """Goes negative when over — budgets says it, never clips it."""
    per_day: int | None
    projected: int | None
    over: int | None
    used: float
    """`spent / target`, unclamped — the 80% alert threshold reads this."""


@dataclass(frozen=True)
class CategoryCapView:
    id: str
    category_id: str
    target: int
    spent: int
    remaining: int
    over: int | None
    used: float


@dataclass(frozen=True)
class BudgetsView:
    period: str
    days_left: int
    month: CapView | None
    categories: tuple[CategoryCapView, ...]


class BudgetsReader(Protocol):
    async def snapshot(self, user_id: UUID, currency: str, today: str) -> BudgetsView: ...
