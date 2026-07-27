from typing import cast
from uuid import UUID

from src.modules.subscriptions.adapters.outbound.persistence.documents.subscription_charge_document import (  # noqa: E501
    SubscriptionChargeDocument,
)
from src.modules.subscriptions.domain.entities.subscription_charge import (
    ChargeStatus,
    SubscriptionCharge,
)


class ChargeMapper:
    @staticmethod
    def to_domain(doc: SubscriptionChargeDocument) -> SubscriptionCharge:
        return SubscriptionCharge(
            id=doc.id,
            user_id=UUID(doc.user_id),
            subscription_id=doc.subscription_id,
            due_on=doc.due_on,
            amount=doc.amount,
            currency=doc.currency,
            status=cast(ChargeStatus, doc.status),
            opened_at=doc.opened_at,
            settled_at=doc.settled_at,
            movement_id=doc.movement_id,
        )

    @staticmethod
    def to_document(charge: SubscriptionCharge) -> SubscriptionChargeDocument:
        return SubscriptionChargeDocument(
            id=charge.id,
            user_id=str(charge.user_id),
            subscription_id=charge.subscription_id,
            due_on=charge.due_on,
            amount=charge.amount,
            currency=charge.currency,
            status=charge.status,
            opened_at=charge.opened_at,
            settled_at=charge.settled_at,
            movement_id=charge.movement_id,
        )
