from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class SubscriptionDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    name: str
    amount: int
    currency: str
    frequency: str
    # The cadence anchor, a date without time: every charge date is derived from it
    # (see domain/schedule.py), so nothing has to advance a "next charge" field.
    first_charge_on: str
    source_type: str
    source_id: str
    category_id: str | None = None
    icon: str
    color: str
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "subscriptions"
        indexes: ClassVar[list[IndexModel]] = [
            # Serves the user's list and, with `active` first, the opener's sweep
            # across tenants (which reads only what is running).
            IndexModel(
                [("active", pymongo.ASCENDING), ("user_id", pymongo.ASCENDING)],
                name="ix_active_user",
            ),
        ]
