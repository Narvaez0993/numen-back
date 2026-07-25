from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel

IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60


class IdempotencyKeyDocument(Document):
    """A client key already spent, pointing at what it produced."""

    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    key: str
    movement_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "idempotency_keys"
        indexes: ClassVar[list[IndexModel]] = [
            # Uniqueness is the guard itself: a racing duplicate fails here.
            IndexModel(
                [("user_id", pymongo.ASCENDING), ("key", pymongo.ASCENDING)],
                unique=True,
                name="uq_user_key",
            ),
            # Keys are only useful while a client might retry: Mongo drops them
            # after a day, no cleanup job needed.
            IndexModel(
                [("created_at", pymongo.ASCENDING)],
                expireAfterSeconds=IDEMPOTENCY_TTL_SECONDS,
                name="ttl_created_at",
            ),
        ]
