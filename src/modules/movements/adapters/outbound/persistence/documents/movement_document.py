from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class MovementDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    type: str
    description: str
    amount: int
    currency: str
    source_type: str
    source_id: str
    destination_type: str | None = None
    destination_id: str | None = None
    category_id: str | None = None
    # Date without time: the day the user says it happened (timezone-proof, and
    # ISO strings compare correctly for range queries).
    occurred_on: str
    captured_via: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "movements"
        # Serves the month listing and gives it a stable order in one index:
        # every query is tenant-scoped and sorted newest first.
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel(
                [
                    ("user_id", pymongo.ASCENDING),
                    ("occurred_on", pymongo.DESCENDING),
                    ("created_at", pymongo.DESCENDING),
                ],
                name="ix_user_date",
            ),
        ]
