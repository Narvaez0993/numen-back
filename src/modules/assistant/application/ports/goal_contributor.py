"""Outbound port: applying a contribute play as a real transfer.

Goals' `ContributeUseCase` does the moving (a real movement, cash-basis deltas
included), so there is no id to return — the money IS the record. Errors come
back as `PlayExecutionError` (`gone`, `invalid_account`).
"""

from typing import Protocol
from uuid import UUID


class GoalContributor(Protocol):
    async def contribute(
        self,
        user_id: UUID,
        *,
        currency: str,
        today: str,
        goal_id: str,
        account_id: str,
        amount: int,
    ) -> None: ...
