"""Outbound port: applying a cap play as a real budget.

The implementation goes through budgets' own use cases (gates included: the
Free limit defends itself here too) and translates that module's errors into
`PlayExecutionError` codes — the play records WHY it failed, never a stack.
"""

from typing import Protocol
from uuid import UUID


class BudgetWriter(Protocol):
    async def create_cap(
        self,
        user_id: UUID,
        *,
        tier: str,
        today: str,
        scope: str,
        category_id: str | None,
        target: int,
    ) -> str:
        """Returns the new budget's id. Raises `PlayExecutionError` with
        `plan_limit`, `already_exists` or `gone`."""
        ...

    async def raise_cap(self, user_id: UUID, *, today: str, budget_id: str, target: int) -> str:
        """Returns the budget's id. Raises `PlayExecutionError` with `gone`."""
        ...
