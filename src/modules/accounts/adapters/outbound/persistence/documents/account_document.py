from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class AccountDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    kind: str
    name: str
    sub: str = ""
    icon: str
    color: str
    currency: str
    balance: int
    initial_balance: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "accounts"
        # Serves every query (all are tenant-scoped) and gives the list a stable
        # order without a second index.
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel(
                [("user_id", pymongo.ASCENDING), ("created_at", pymongo.ASCENDING)],
                name="ix_user_created",
            ),
        ]
