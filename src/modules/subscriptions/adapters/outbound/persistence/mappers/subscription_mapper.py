from typing import cast
from uuid import UUID

from src.modules.subscriptions.adapters.outbound.persistence.documents.subscription_document import (  # noqa: E501
    SubscriptionDocument,
)
from src.modules.subscriptions.domain.entities.subscription import (
    Frequency,
    SourceRef,
    SourceType,
    Subscription,
)


class SubscriptionMapper:
    @staticmethod
    def to_domain(doc: SubscriptionDocument) -> Subscription:
        return Subscription(
            id=doc.id,
            user_id=UUID(doc.user_id),
            name=doc.name,
            amount=doc.amount,
            currency=doc.currency,
            frequency=cast(Frequency, doc.frequency),
            first_charge_on=doc.first_charge_on,
            source=SourceRef(type=cast(SourceType, doc.source_type), id=doc.source_id),
            category_id=doc.category_id,
            icon=doc.icon,
            color=doc.color,
            active=doc.active,
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(subscription: Subscription) -> SubscriptionDocument:
        return SubscriptionDocument(
            id=subscription.id,
            user_id=str(subscription.user_id),
            name=subscription.name,
            amount=subscription.amount,
            currency=subscription.currency,
            frequency=subscription.frequency,
            first_charge_on=subscription.first_charge_on,
            source_type=subscription.source.type,
            source_id=subscription.source.id,
            category_id=subscription.category_id,
            icon=subscription.icon,
            color=subscription.color,
            active=subscription.active,
            created_at=subscription.created_at,
        )
