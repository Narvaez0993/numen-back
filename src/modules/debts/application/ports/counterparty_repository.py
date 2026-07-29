from typing import Protocol
from uuid import UUID

from src.modules.debts.domain.entities.counterparty import Counterparty


class CounterpartyRepository(Protocol):
    """Outbound port: the people money is between (per user)."""

    async def list_by_user(self, user_id: UUID) -> list[Counterparty]: ...

    async def find(self, user_id: UUID, counterparty_id: str) -> Counterparty | None: ...

    async def find_by_name(self, user_id: UUID, name: str) -> Counterparty | None:
        """Matched on the normalized `name_key`, so "juan" finds "Juan"."""
        ...

    async def save(self, counterparty: Counterparty) -> None: ...
