from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import BaseModel, Field
from pymongo import IndexModel


class PaymentEntry(BaseModel):
    id: str
    amount: int
    paid_on: str
    note: str | None = None


class DebtDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    direction: str
    counterparty_id: str
    amount: int
    currency: str
    # `YYYY-MM-DD` or null — never a display string; a stored "21 may" is the bug that
    # broke `overdue` in the prototype.
    due_on: str | None = None
    note: str | None = None
    event_id: str | None = None
    # Embedded: payments only ever live with their debt, and a user's debts are dozens.
    # What is left is DERIVED from these — no `balance` field, on purpose.
    payments: list[PaymentEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "debts"
        indexes: ClassVar[list[IndexModel]] = [
            # Serves every read: the user's list, and the event sibling check on delete.
            IndexModel(
                [("user_id", pymongo.ASCENDING), ("event_id", pymongo.ASCENDING)],
                name="ix_user_event",
            ),
        ]
