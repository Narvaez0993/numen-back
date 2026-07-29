from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class GoalView:
    id: str
    name: str
    target: int
    saved: int
    pct: float
    achieved: bool
    archived: bool
    target_date: str | None
    projected_on: str | None
    needed_per_month: int | None


class GoalsReader(Protocol):
    async def snapshot(self, user_id: UUID, currency: str, today: str) -> tuple[GoalView, ...]: ...
