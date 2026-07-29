from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class MovementDraftDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    currency: str
    type: str
    description: str
    amount: int
    source_type: str
    source_id: str
    destination_type: str | None = None
    destination_id: str | None = None
    category_id: str | None = None
    occurred_on: str
    status: str
    movement_id: str | None = None
    # Default keeps pre-voice drafts readable: they were all typed.
    captured_via: str = "text"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "assistant_movement_drafts"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel(
                [("user_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING)],
                name="ix_user_status",
            ),
        ]
