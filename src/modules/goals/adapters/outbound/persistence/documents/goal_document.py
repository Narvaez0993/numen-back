from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class GoalDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    name: str
    icon: str
    color: str
    target: int
    currency: str
    target_date: str | None = None
    # No `saved` on purpose: the pocket's money is the sum of its transfer movements,
    # recomputed on read — a stored copy is the field that drifts.
    archived_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "goals"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel([("user_id", pymongo.ASCENDING)], name="ix_user"),
        ]
