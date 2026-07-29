from collections.abc import Sequence
from uuid import UUID

from src.modules.assistant.adapters.outbound.persistence.documents.movement_draft_document import (
    MovementDraftDocument,
)
from src.modules.assistant.adapters.outbound.persistence.mappers.movement_draft_mapper import (
    MovementDraftMapper,
)
from src.modules.assistant.domain.entities.movement_draft import MovementDraft
from src.shared.adapters.outbound.persistence.mongo import current_session


class MongoMovementDraftRepository:
    """Beanie/Mongo implementation of `DraftRepository`."""

    async def save(self, draft: MovementDraft) -> None:
        session = current_session()
        existing = await MovementDraftDocument.get(draft.id, session=session)
        if existing is None:
            await MovementDraftMapper.to_document(draft).insert(session=session)
            return
        fresh = MovementDraftMapper.to_document(draft)
        existing.type = fresh.type
        existing.description = fresh.description
        existing.amount = fresh.amount
        existing.source_type = fresh.source_type
        existing.source_id = fresh.source_id
        existing.destination_type = fresh.destination_type
        existing.destination_id = fresh.destination_id
        existing.category_id = fresh.category_id
        existing.occurred_on = fresh.occurred_on
        existing.status = fresh.status
        existing.movement_id = fresh.movement_id
        await existing.save(session=session)

    async def save_many(self, drafts: Sequence[MovementDraft]) -> None:
        for draft in drafts:
            await self.save(draft)

    async def find(self, user_id: UUID, draft_id: str) -> MovementDraft | None:
        doc = await MovementDraftDocument.find_one(
            MovementDraftDocument.id == draft_id,
            MovementDraftDocument.user_id == str(user_id),
        )
        return MovementDraftMapper.to_domain(doc) if doc else None

    async def find_many(self, user_id: UUID, draft_ids: Sequence[str]) -> tuple[MovementDraft, ...]:
        docs = await MovementDraftDocument.find(
            {"user_id": str(user_id), "_id": {"$in": list(draft_ids)}}
        ).to_list()
        return tuple(MovementDraftMapper.to_domain(doc) for doc in docs)
