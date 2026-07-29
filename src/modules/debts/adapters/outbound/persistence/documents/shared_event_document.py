from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class SharedEventDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    name: str
    total: int
    occurred_on: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "debt_shared_events"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel([("user_id", pymongo.ASCENDING)], name="ix_user"),
        ]
