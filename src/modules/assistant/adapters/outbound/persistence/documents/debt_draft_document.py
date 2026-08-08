from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class DebtDraftDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    currency: str
    direction: str
    counterparty_id: str | None = None
    counterparty_name: str
    amount: int
    # Null is a real answer, not a missing one: a split moves no cash.
    account_id: str | None = None
    due_on: str | None = None
    note: str | None = None
    status: str
    debt_id: str | None = None
    # Default keeps pre-payment drafts readable: they could only ever open a debt.
    kind: str = "new"
    target_debt_id: str | None = None
    captured_via: str = "text"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "assistant_debt_drafts"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel(
                [("user_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING)],
                name="ix_user_status",
            ),
        ]
