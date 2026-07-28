from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class CounterpartyDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    name: str
    # The normalized form ("juan felipe") the dedup runs on; `name` keeps the spelling
    # the user typed.
    name_key: str
    color: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "debt_counterparties"
        indexes: ClassVar[list[IndexModel]] = [
            # One person per normalized name — the rule lives in the store, so two
            # concurrent creates cannot mint twins of "Juan".
            IndexModel(
                [("user_id", pymongo.ASCENDING), ("name_key", pymongo.ASCENDING)],
                name="ux_user_name_key",
                unique=True,
            ),
        ]
