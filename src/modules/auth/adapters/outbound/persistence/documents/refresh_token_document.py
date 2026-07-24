from datetime import datetime
from typing import Annotated, ClassVar
from uuid import UUID, uuid4

import pymongo
from beanie import Document, Indexed
from pydantic import Field


class RefreshTokenDocument(Document):
    id: UUID = Field(default_factory=uuid4)  # type: ignore[assignment]
    user_id: UUID
    token_hash: Annotated[str, Indexed(unique=True)]
    family_id: UUID
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None = None

    class Settings:
        name = "refresh_tokens"
        indexes: ClassVar[list[list[tuple[str, int]]]] = [
            [("family_id", pymongo.ASCENDING)],
        ]
