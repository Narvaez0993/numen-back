from uuid import UUID

from src.modules.assistant.adapters.outbound.persistence.documents.usage_counter_document import (
    AIUsageCounterDocument,
)
from src.modules.assistant.application.ports.usage_counters import UsageView
from src.shared.adapters.outbound.persistence.mongo import current_session


class MongoAIUsageCounters:
    """Beanie/Mongo implementation of `UsageCounters`.

    `consume` is a raw `$inc` upsert on the unique `(user, period)` key: atomic
    under concurrency, month-resetting by construction, and valid inside the
    turn's transaction (the session travels with it).
    """

    async def month_usage(self, user_id: UUID, period: str) -> UsageView:
        doc = await AIUsageCounterDocument.find_one(
            AIUsageCounterDocument.user_id == str(user_id),
            AIUsageCounterDocument.period == period,
        )
        if doc is None:
            return UsageView(registrations_used=0, messages_used=0)
        return UsageView(registrations_used=doc.registrations_used, messages_used=doc.messages_used)

    async def consume(
        self, user_id: UUID, period: str, *, registrations: int, messages: int
    ) -> None:
        collection = AIUsageCounterDocument.get_pymongo_collection()
        await collection.update_one(
            {"user_id": str(user_id), "period": period},
            {
                "$inc": {"registrations_used": registrations, "messages_used": messages},
                "$setOnInsert": {"_id": f"{user_id}:{period}"},
            },
            upsert=True,
            session=current_session(),
        )
