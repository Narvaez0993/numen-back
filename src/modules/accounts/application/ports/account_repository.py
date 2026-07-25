from typing import Protocol
from uuid import UUID

from src.modules.accounts.domain.entities.account import Account


class AccountRepository(Protocol):
    """Outbound port: persistence of `Account` aggregates (per user).

    The set per user is small (bounded by the plan), so callers list it to both
    count for the capacity gate and build the overview in one indexed query.
    """

    async def list_by_user(self, user_id: UUID) -> list[Account]: ...

    async def find(self, user_id: UUID, account_id: str) -> Account | None: ...

    async def save(self, account: Account) -> None: ...

    async def delete(self, user_id: UUID, account_id: str) -> None: ...
