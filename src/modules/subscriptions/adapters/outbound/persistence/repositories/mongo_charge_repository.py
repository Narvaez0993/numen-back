from datetime import datetime
from typing import Any
from uuid import UUID

from pymongo.errors import DuplicateKeyError

from src.modules.subscriptions.adapters.outbound.persistence.documents.subscription_charge_document import (  # noqa: E501
    SubscriptionChargeDocument,
)
from src.modules.subscriptions.adapters.outbound.persistence.mappers.charge_mapper import (
    ChargeMapper,
)
from src.modules.subscriptions.application.ports.charge_repository import (
    ChargeAlreadyOpenError,
)
from src.modules.subscriptions.domain.entities.subscription_charge import SubscriptionCharge
from src.shared.adapters.outbound.persistence.mongo import current_session


class MongoChargeRepository:
    """`ChargeRepository` over the `subscription_charges` collection.

    `open` leans on the unique `(user_id, subscription_id, due_on)` index rather than
    a check-then-write: two concurrent job runs both try to insert, one wins and the
    other is told the charge already exists.
    """

    async def open(self, charge: SubscriptionCharge) -> None:
        try:
            await ChargeMapper.to_document(charge).insert(session=current_session())
        except DuplicateKeyError as exc:
            raise ChargeAlreadyOpenError(charge.subscription_id) from exc

    async def save(self, charge: SubscriptionCharge) -> None:
        session = current_session()
        existing = await SubscriptionChargeDocument.get(charge.id, session=session)
        if existing is None:
            await ChargeMapper.to_document(charge).insert(session=session)
            return
        existing.amount = charge.amount
        existing.status = charge.status
        existing.settled_at = charge.settled_at
        existing.movement_id = charge.movement_id
        await existing.save(session=session)

    async def find(self, user_id: UUID, charge_id: str) -> SubscriptionCharge | None:
        doc = await SubscriptionChargeDocument.find_one(
            SubscriptionChargeDocument.id == charge_id,
            SubscriptionChargeDocument.user_id == str(user_id),
        )
        return ChargeMapper.to_domain(doc) if doc else None

    async def list_by_status(
        self, user_id: UUID, status: str | None = None
    ) -> list[SubscriptionCharge]:
        criteria: dict[str, Any] = {"user_id": str(user_id)}
        if status is not None:
            criteria["status"] = status
        docs = await SubscriptionChargeDocument.find(criteria).to_list()
        return [ChargeMapper.to_domain(doc) for doc in docs]

    async def list_pending_before(self, deadline: datetime) -> list[SubscriptionCharge]:
        docs = await SubscriptionChargeDocument.find(
            {"status": "pending", "opened_at": {"$lte": deadline}}
        ).to_list()
        return [ChargeMapper.to_domain(doc) for doc in docs]
