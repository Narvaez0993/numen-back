from datetime import UTC, datetime
from typing import Annotated, ClassVar
from uuid import uuid4

import pymongo
from beanie import Document, Indexed
from pydantic import BaseModel, Field

from src.shared.domain.money import DEFAULT_CURRENCY


class UserPreferencesDocument(BaseModel):
    """Embedded preferences. Defaults cover documents written before this field
    existed, so no migration is needed."""

    language: str = "es"
    currency: str = DEFAULT_CURRENCY
    theme: str = "system"


class UserDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    email: Annotated[str, Indexed(unique=True)]
    display_name: str
    hashed_password: str
    tier: str = "free"
    email_verified: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    preferences: UserPreferencesDocument = Field(default_factory=UserPreferencesDocument)

    class Settings:
        name = "users"
        indexes: ClassVar[list[list[tuple[str, int]]]] = [
            [("email", pymongo.ASCENDING)],
        ]
