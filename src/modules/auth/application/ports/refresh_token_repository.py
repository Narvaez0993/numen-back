from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.auth.domain.entities.refresh_token import RefreshToken


class RefreshTokenRepository(Protocol):
    """Outbound port: persistence of rotating refresh tokens."""

    async def save(self, token: RefreshToken) -> None: ...

    async def find_by_hash(self, token_hash: str) -> RefreshToken | None: ...

    async def revoke_family(self, family_id: UUID, revoked_at: datetime) -> None: ...
