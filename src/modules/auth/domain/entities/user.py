from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from src.modules.auth.domain.value_objects.email import Email
from src.modules.auth.domain.value_objects.hashed_password import HashedPassword
from src.modules.auth.domain.value_objects.preferences import UserPreferences

Tier = Literal["free", "plus"]


@dataclass(frozen=True)
class User:
    id: UUID
    email: Email
    display_name: str
    hashed_password: HashedPassword
    tier: Tier
    email_verified: bool
    created_at: datetime
    preferences: UserPreferences

    @classmethod
    def new(
        cls,
        email: Email,
        display_name: str,
        hashed_password: HashedPassword,
        created_at: datetime,
        language: str = "es",
        currency: str | None = None,
    ) -> "User":
        return cls(
            id=uuid4(),
            email=email,
            display_name=display_name,
            hashed_password=hashed_password,
            tier="free",
            email_verified=False,
            created_at=created_at,
            preferences=UserPreferences.default(language=language, currency=currency),
        )

    def with_password(self, hashed_password: HashedPassword) -> "User":
        return replace(self, hashed_password=hashed_password)

    def verified(self) -> "User":
        return replace(self, email_verified=True)

    def upgrade_to_plus(self) -> "User":
        return replace(self, tier="plus")

    def with_display_name(self, display_name: str) -> "User":
        return replace(self, display_name=display_name)

    def with_preferences(self, preferences: UserPreferences) -> "User":
        return replace(self, preferences=preferences)
