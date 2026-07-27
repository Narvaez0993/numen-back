from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class SubscriptionChargeDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    subscription_id: str
    # The day it is due — a date, so it matches the movement's `occurred_on`.
    due_on: str
    amount: int
    currency: str
    status: str
    opened_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    settled_at: datetime | None = None
    movement_id: str | None = None

    class Settings:
        name = "subscription_charges"
        indexes: ClassVar[list[IndexModel]] = [
            # Uniqueness *is* the idempotency: two runs of the opener cannot create
            # the same day's charge twice, and no check-then-write race exists.
            IndexModel(
                [
                    ("user_id", pymongo.ASCENDING),
                    ("subscription_id", pymongo.ASCENDING),
                    ("due_on", pymongo.ASCENDING),
                ],
                unique=True,
                name="uq_user_subscription_due",
            ),
            # The settler's sweep across tenants: pending, oldest first.
            IndexModel(
                [("status", pymongo.ASCENDING), ("opened_at", pymongo.ASCENDING)],
                name="ix_status_opened",
            ),
        ]
