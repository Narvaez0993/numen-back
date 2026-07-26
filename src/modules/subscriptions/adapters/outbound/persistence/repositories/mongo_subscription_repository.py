from typing import Any
from uuid import UUID

from src.modules.subscriptions.adapters.outbound.persistence.documents.subscription_document import (  # noqa: E501
    SubscriptionDocument,
)
from src.modules.subscriptions.adapters.outbound.persistence.mappers.subscription_mapper import (
    SubscriptionMapper,
)
from src.modules.subscriptions.domain.entities.subscription import Subscription
from src.shared.adapters.outbound.persistence.mongo import current_session


class MongoSubscriptionRepository:
    """Beanie/Mongo implementation of `SubscriptionRepository`.

    Every user-facing read is tenant-scoped. `list_active` is the one exception and
    it exists for the charge opener, which sweeps every tenant on a schedule — it is
    served by the `(active, user_id)` index.
    """

    async def list_by_user(self, user_id: UUID, *, only_active: bool = False) -> list[Subscription]:
        criteria: dict[str, Any] = {"user_id": str(user_id)}
        if only_active:
            criteria["active"] = True
        docs = await SubscriptionDocument.find(criteria).to_list()
        return [SubscriptionMapper.to_domain(doc) for doc in docs]

    async def list_active(self) -> list[Subscription]:
        docs = await SubscriptionDocument.find({"active": True}).to_list()
        return [SubscriptionMapper.to_domain(doc) for doc in docs]

    async def find(self, user_id: UUID, subscription_id: str) -> Subscription | None:
        doc = await SubscriptionDocument.find_one(
            SubscriptionDocument.id == subscription_id,
            SubscriptionDocument.user_id == str(user_id),
        )
        return SubscriptionMapper.to_domain(doc) if doc else None

    async def save(self, subscription: Subscription) -> None:
        session = current_session()
        existing = await SubscriptionDocument.get(subscription.id, session=session)
        if existing is None:
            await SubscriptionMapper.to_document(subscription).insert(session=session)
            return
        existing.name = subscription.name
        existing.amount = subscription.amount
        existing.currency = subscription.currency
        existing.frequency = subscription.frequency
        existing.first_charge_on = subscription.first_charge_on
        existing.source_type = subscription.source.type
        existing.source_id = subscription.source.id
        existing.category_id = subscription.category_id
        existing.icon = subscription.icon
        existing.color = subscription.color
        existing.active = subscription.active
        await existing.save(session=session)

    async def delete(self, user_id: UUID, subscription_id: str) -> bool:
        doc = await SubscriptionDocument.find_one(
            SubscriptionDocument.id == subscription_id,
            SubscriptionDocument.user_id == str(user_id),
        )
        if doc is None:
            return False
        await doc.delete(session=current_session())
        return True
