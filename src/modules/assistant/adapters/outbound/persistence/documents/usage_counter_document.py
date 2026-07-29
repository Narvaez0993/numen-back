from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class AIUsageCounterDocument(Document):
    """One row per `(user, YYYY-MM)`. The unique key IS the month reset: a new
    period upserts a fresh row at zero, so no job has to run on the 1st."""

    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    period: str
    registrations_used: int = 0
    messages_used: int = 0

    class Settings:
        name = "assistant_usage_counters"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel(
                [("user_id", pymongo.ASCENDING), ("period", pymongo.ASCENDING)],
                name="uq_user_period",
                unique=True,
            ),
        ]
