from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from src.modules.assistant.adapters.outbound.persistence.documents.dismissal_document import (
    InsightDismissalDocument,
)


class MongoInsightDismissals:
    """Beanie/Mongo implementation of `InsightDismissals` — upsert + one `$in`."""

    async def dismiss(self, user_id: UUID, key: str, at: datetime) -> None:
        collection = InsightDismissalDocument.get_pymongo_collection()
        await collection.update_one(
            {"user_id": str(user_id), "key": key},
            {
                "$set": {"dismissed_at": at},
                "$setOnInsert": {"_id": f"{user_id}:{key}"},
            },
            upsert=True,
        )

    async def dismissed_among(self, user_id: UUID, keys: Sequence[str]) -> frozenset[str]:
        docs = await InsightDismissalDocument.find(
            {"user_id": str(user_id), "key": {"$in": list(keys)}}
        ).to_list()
        return frozenset(doc.key for doc in docs)
