from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class AIActionLogDocument(Document):
    """The cost ledger — one row per model action, failed calls included. This
    is the guardrail of docs/07: margin is measured, not hoped for."""

    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    action: str
    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float
    period: str
    failed: bool
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "assistant_action_logs"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel(
                [("user_id", pymongo.ASCENDING), ("at", pymongo.DESCENDING)],
                name="ix_user_at",
            ),
        ]
