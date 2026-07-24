from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class RefreshToken:
    """A rotating refresh token, persisted as a SHA-256 hash of the opaque value.

    Tokens issued from the same login form a family. Rotation revokes the used
    token and issues its successor in the same family; presenting an already
    revoked token is treated as theft and revokes the whole family.
    """

    id: UUID
    user_id: UUID
    token_hash: str
    family_id: UUID
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None

    @classmethod
    def issue(
        cls,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        created_at: datetime,
        family_id: UUID | None = None,
    ) -> "RefreshToken":
        return cls(
            id=uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id or uuid4(),
            expires_at=expires_at,
            created_at=created_at,
            revoked_at=None,
        )

    def is_active(self, now: datetime) -> bool:
        return self.revoked_at is None and now < self.expires_at

    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def revoke(self, now: datetime) -> "RefreshToken":
        return replace(self, revoked_at=now)
