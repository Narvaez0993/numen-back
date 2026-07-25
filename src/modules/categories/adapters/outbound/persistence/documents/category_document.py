from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

import pymongo
from beanie import Document
from pydantic import Field
from pymongo import IndexModel


class CategoryDocument(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))  # type: ignore[assignment]
    user_id: str
    name: str
    icon: str
    color: str
    flow: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "categories"
        # Compound unique index: prevents duplicate (name, flow) per tenant AND
        # serves list/count-by-user (user_id is the prefix). One index, two jobs.
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel(
                [
                    ("user_id", pymongo.ASCENDING),
                    ("flow", pymongo.ASCENDING),
                    ("name", pymongo.ASCENDING),
                ],
                unique=True,
                name="uq_user_flow_name",
            ),
        ]
