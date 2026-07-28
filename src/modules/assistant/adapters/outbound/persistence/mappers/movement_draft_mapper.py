from uuid import UUID

from src.modules.assistant.adapters.outbound.persistence.documents.movement_draft_document import (
    MovementDraftDocument,
)
from src.modules.assistant.domain.entities.movement_draft import MovementDraft


class MovementDraftMapper:
    @staticmethod
    def to_domain(doc: MovementDraftDocument) -> MovementDraft:
        return MovementDraft(
            id=doc.id,
            user_id=UUID(doc.user_id),
            currency=doc.currency,
            type=doc.type,
            description=doc.description,
            amount=doc.amount,
            source_type=doc.source_type,
            source_id=doc.source_id,
            destination_type=doc.destination_type,
            destination_id=doc.destination_id,
            category_id=doc.category_id,
            occurred_on=doc.occurred_on,
            status=doc.status,
            movement_id=doc.movement_id,
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(draft: MovementDraft) -> MovementDraftDocument:
        return MovementDraftDocument(
            id=draft.id,
            user_id=str(draft.user_id),
            currency=draft.currency,
            type=draft.type,
            description=draft.description,
            amount=draft.amount,
            source_type=draft.source_type,
            source_id=draft.source_id,
            destination_type=draft.destination_type,
            destination_id=draft.destination_id,
            category_id=draft.category_id,
            occurred_on=draft.occurred_on,
            status=draft.status,
            movement_id=draft.movement_id,
            created_at=draft.created_at,
        )
