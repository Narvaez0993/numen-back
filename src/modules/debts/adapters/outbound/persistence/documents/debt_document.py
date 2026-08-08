from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


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
    # The day the user gave up on it, or null. The decision is stored; what it cost
    # is not — that is the expense movement the write-off recorded.
    written_off_on: str | None = None
    # No `payments` and no `balance`, on purpose: repayments are transfer movements
    # now, and what is left is derived from them. A stored copy is exactly the second
    # source of truth this module keeps killing.
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
