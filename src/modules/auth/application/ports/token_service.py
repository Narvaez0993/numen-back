from typing import Protocol
from uuid import UUID


class TokenService(Protocol):
    """Outbound port: issues access tokens for authenticated sessions."""

    def issue_access_token(self, user_id: UUID, tier: str) -> str: ...
