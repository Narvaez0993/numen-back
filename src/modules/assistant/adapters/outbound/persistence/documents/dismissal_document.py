from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel

# Dismissal keys carry their period ("cap:comida:2026-08"), so rows stop
# mattering on their own; the TTL just keeps the collection from growing forever.
_TTL_DAYS = 120


class InsightDismissalDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    key: str
    dismissed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "assistant_insight_dismissals"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel(
                [("user_id", pymongo.ASCENDING), ("key", pymongo.ASCENDING)],
                name="uq_user_key",
                unique=True,
            ),
            IndexModel(
                [("dismissed_at", pymongo.ASCENDING)],
                name="ttl_dismissed_at",
                expireAfterSeconds=_TTL_DAYS * 24 * 3600,
            ),
        ]
