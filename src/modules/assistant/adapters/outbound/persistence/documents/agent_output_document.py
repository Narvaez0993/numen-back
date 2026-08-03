from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class AgentOutputDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    kind: str
    period: str
    payload: dict[str, Any]
    plays: list[dict[str, Any]]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    read_at: datetime | None = None
    dismissed_at: datetime | None = None

    class Settings:
        name = "assistant_agent_outputs"
        indexes: ClassVar[list[IndexModel]] = [
            # The job's idempotency: one Corte per user per month, by construction.
            IndexModel(
                [
                    ("user_id", pymongo.ASCENDING),
                    ("kind", pymongo.ASCENDING),
                    ("period", pymongo.ASCENDING),
                ],
                name="uq_user_kind_period",
                unique=True,
            ),
            IndexModel(
                [("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)],
                name="ix_user_created",
            ),
        ]
