from typing import Protocol
from uuid import UUID

from src.modules.accounts.domain.entities.credit_card import CreditCard


class CreditCardRepository(Protocol):
    """Outbound port: persistence of `CreditCard` aggregates (per user)."""

    async def list_by_user(self, user_id: UUID) -> list[CreditCard]: ...

    async def find(self, user_id: UUID, card_id: str) -> CreditCard | None: ...

    async def save(self, card: CreditCard) -> None: ...

    async def delete(self, user_id: UUID, card_id: str) -> None: ...
