from typing import Protocol
from uuid import UUID

from src.modules.auth.domain.entities.user import User
from src.modules.auth.domain.value_objects.email import Email


class AuthRepository(Protocol):
    """Outbound port: persistence of `User` aggregates."""

    async def find_by_id(self, user_id: UUID) -> User | None: ...

    async def find_by_email(self, email: Email) -> User | None: ...

    async def save(self, user: User) -> None: ...
