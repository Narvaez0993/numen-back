from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class TopGoalView:
    """The pocket Home leads with, already measured by the module that owns it.

    Home never divides or projects goal money itself — two implementations of the
    same pocket would eventually disagree on the same screen day.
    """

    name: str
    target: int
    saved: int
    pct: float
    projected_on: str | None


class GoalReader(Protocol):
    """Outbound port: the active goal closest to done, or `None` without one."""

    async def top_goal(self, user_id: UUID, today: str) -> TopGoalView | None: ...
