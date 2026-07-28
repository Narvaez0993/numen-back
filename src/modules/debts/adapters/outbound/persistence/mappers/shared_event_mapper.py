from uuid import UUID

from src.modules.debts.adapters.outbound.persistence.documents.shared_event_document import (
    SharedEventDocument,
)
from src.modules.debts.domain.entities.shared_event import SharedEvent


class SharedEventMapper:
    @staticmethod
    def to_domain(doc: SharedEventDocument) -> SharedEvent:
        return SharedEvent(
            id=doc.id,
            user_id=UUID(doc.user_id),
            name=doc.name,
            total=doc.total,
            occurred_on=doc.occurred_on,
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(event: SharedEvent) -> SharedEventDocument:
        return SharedEventDocument(
            id=event.id,
            user_id=str(event.user_id),
            name=event.name,
            total=event.total,
            occurred_on=event.occurred_on,
            created_at=event.created_at,
        )
