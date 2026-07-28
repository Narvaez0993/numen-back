from typing import Protocol
from uuid import UUID

from src.modules.goals.domain.entities.goal import Goal


class GoalRepository(Protocol):
    """Outbound port: persistence of `Goal` (per user)."""

    async def list_by_user(self, user_id: UUID) -> list[Goal]: ...

    async def find(self, user_id: UUID, goal_id: str) -> Goal | None: ...

    async def save(self, goal: Goal) -> None: ...

    async def delete(self, user_id: UUID, goal_id: str) -> None: ...
