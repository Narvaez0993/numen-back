from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class CreditCardDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    name: str
    icon: str
    color: str
    currency: str
    debt: int
    initial_debt: int
    limit: int
    cutoff_day: int
    due_day: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "credit_cards"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel(
                [("user_id", pymongo.ASCENDING), ("created_at", pymongo.ASCENDING)],
                name="ix_user_created",
            ),
        ]
