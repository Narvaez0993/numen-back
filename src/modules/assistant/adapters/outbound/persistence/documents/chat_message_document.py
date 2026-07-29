from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class ChatMessageDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    role: str
    blocks: list[dict[str, Any]]
    # Set by the client to make a retried send idempotent; unique per user when present.
    client_message_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "assistant_chat_messages"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel(
                [("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
                name="ix_user_created",
            ),
            IndexModel(
                [("user_id", pymongo.ASCENDING), ("client_message_id", pymongo.ASCENDING)],
                name="uq_user_client_message",
                unique=True,
                partialFilterExpression={"client_message_id": {"$type": "string"}},
            ),
        ]
