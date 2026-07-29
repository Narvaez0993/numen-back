from typing import Protocol
from uuid import UUID

from src.modules.debts.domain.entities.debt import Debt


class DebtRepository(Protocol):
    """Outbound port: persistence of `Debt` (per user).

    There is no aggregate read here on purpose: a user's debts are dozens, not
    thousands, so every consumer loads the list and derives with the same pure
    functions (`status.py`) — one code path, so the screen and Home cannot disagree.
    """

    async def list_by_user(self, user_id: UUID) -> list[Debt]: ...

    async def list_by_event(self, user_id: UUID, event_id: str) -> list[Debt]: ...

    async def find(self, user_id: UUID, debt_id: str) -> Debt | None: ...

    async def save(self, debt: Debt) -> None: ...

    async def delete(self, user_id: UUID, debt_id: str) -> None: ...
