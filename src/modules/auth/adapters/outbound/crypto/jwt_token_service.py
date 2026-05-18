from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt


@dataclass
class JwtTokenService:
    """`TokenService` implementation backed by PyJWT (HS256 default)."""

    secret: str
    algorithm: str
    access_ttl_minutes: int

    def issue_access_token(self, user_id: UUID, tier: str) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "tier": tier,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self.access_ttl_minutes)).timestamp()),
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)
