from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from src.modules.auth.domain.value_objects.email import Email
from src.modules.auth.domain.value_objects.hashed_password import HashedPassword

Tier = Literal["free", "plus"]


@dataclass(frozen=True)
class User:
    id: UUID
    email: Email
    display_name: str
    hashed_password: HashedPassword
    tier: Tier
    created_at: datetime

    @classmethod
    def new(
        cls,
        email: Email,
        display_name: str,
        hashed_password: HashedPassword,
    ) -> "User":
        return cls(
            id=uuid4(),
            email=email,
            display_name=display_name,
            hashed_password=hashed_password,
            tier="free",
            created_at=datetime.now(UTC),
        )

    def with_password(self, hashed_password: HashedPassword) -> "User":
        return replace(self, hashed_password=hashed_password)

    def upgrade_to_plus(self) -> "User":
        return replace(self, tier="plus")
