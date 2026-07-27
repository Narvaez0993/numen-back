from typing import cast
from uuid import UUID

from src.modules.movements.adapters.outbound.persistence.documents.movement_document import (
    MovementDocument,
)
from src.modules.movements.domain.entities.movement import (
    CapturedVia,
    Movement,
    MovementType,
    SourceRef,
    SourceType,
)


class MovementMapper:
    @staticmethod
    def to_domain(doc: MovementDocument) -> Movement:
        destination: SourceRef | None = None
        if doc.destination_type is not None and doc.destination_id is not None:
            destination = SourceRef(
                type=cast(SourceType, doc.destination_type), id=doc.destination_id
            )
        return Movement(
            id=doc.id,
            user_id=UUID(doc.user_id),
            type=cast(MovementType, doc.type),
            description=doc.description,
            amount=doc.amount,
            currency=doc.currency,
            source=SourceRef(type=cast(SourceType, doc.source_type), id=doc.source_id),
            destination=destination,
            category_id=doc.category_id,
            occurred_on=doc.occurred_on,
            captured_via=cast(CapturedVia, doc.captured_via),
            created_at=doc.created_at,
            subscription_id=doc.subscription_id,
        )

    @staticmethod
    def to_document(movement: Movement) -> MovementDocument:
        return MovementDocument(
            id=movement.id,
            user_id=str(movement.user_id),
            type=movement.type,
            description=movement.description,
            amount=movement.amount,
            currency=movement.currency,
            source_type=movement.source.type,
            source_id=movement.source.id,
            destination_type=(
                movement.destination.type if movement.destination is not None else None
            ),
            destination_id=(movement.destination.id if movement.destination is not None else None),
            category_id=movement.category_id,
            occurred_on=movement.occurred_on,
            captured_via=movement.captured_via,
            created_at=movement.created_at,
            subscription_id=movement.subscription_id,
        )
