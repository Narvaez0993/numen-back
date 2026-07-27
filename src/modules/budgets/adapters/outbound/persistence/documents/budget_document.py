from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class BudgetDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    scope: str
    category_id: str | None = None
    target: int
    # `YYYY-MM`: the month the current target was set in. A cap is standing, not
    # monthly, so this is a stamp for later features and never a filter for reads.
    since: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "budgets"
        indexes: ClassVar[list[IndexModel]] = [
            # One global cap per user and one cap per category — the rule lives here and
            # not only in the use case, so two concurrent requests cannot both pass the
            # check and write a second ceiling. Mongo indexes nulls, so the `global`
            # rows (whose `category_id` is null) collide with each other exactly as
            # intended.
            IndexModel(
                [
                    ("user_id", pymongo.ASCENDING),
                    ("scope", pymongo.ASCENDING),
                    ("category_id", pymongo.ASCENDING),
                ],
                name="ux_user_scope_category",
                unique=True,
            ),
        ]
