from typing import Protocol
from uuid import UUID

from src.modules.budgets.domain.entities.budget import Budget


class BudgetRepository(Protocol):
    """Outbound port: persistence of `Budget` (per user)."""

    async def list_by_user(self, user_id: UUID) -> list[Budget]: ...

    async def find(self, user_id: UUID, budget_id: str) -> Budget | None: ...

    async def find_global(self, user_id: UUID) -> Budget | None:
        """The month's ceiling, on its own indexed read.

        Home needs only this one, and it asks for it on every load: making it fetch the
        whole list to filter in memory would be a full scan for one document.
        """
        ...

    async def find_for_category(self, user_id: UUID, category_id: str) -> Budget | None: ...

    async def save(self, budget: Budget) -> None: ...

    async def delete(self, user_id: UUID, budget_id: str) -> None: ...
