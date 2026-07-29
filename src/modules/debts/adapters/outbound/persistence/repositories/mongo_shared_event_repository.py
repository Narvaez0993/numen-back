from uuid import UUID

from src.modules.debts.adapters.outbound.persistence.documents.shared_event_document import (
    SharedEventDocument,
)
from src.modules.debts.adapters.outbound.persistence.mappers.shared_event_mapper import (
    SharedEventMapper,
)
from src.modules.debts.domain.entities.shared_event import SharedEvent
from src.shared.adapters.outbound.persistence.mongo import current_session


class MongoSharedEventRepository:
    """Beanie/Mongo implementation of `EventRepository`."""

    async def list_by_user(self, user_id: UUID) -> list[SharedEvent]:
        docs = await SharedEventDocument.find({"user_id": str(user_id)}).to_list()
        return [SharedEventMapper.to_domain(doc) for doc in docs]

    async def find(self, user_id: UUID, event_id: str) -> SharedEvent | None:
        doc = await SharedEventDocument.find_one(
            SharedEventDocument.id == event_id,
            SharedEventDocument.user_id == str(user_id),
        )
        return SharedEventMapper.to_domain(doc) if doc else None

    async def save(self, event: SharedEvent) -> None:
        session = current_session()
        existing = await SharedEventDocument.get(event.id, session=session)
        if existing is None:
            await SharedEventMapper.to_document(event).insert(session=session)
            return
        existing.name = event.name
        existing.total = event.total
        existing.occurred_on = event.occurred_on
        await existing.save(session=session)

    async def delete(self, user_id: UUID, event_id: str) -> None:
        doc = await SharedEventDocument.find_one(
            SharedEventDocument.id == event_id,
            SharedEventDocument.user_id == str(user_id),
        )
        if doc is not None:
            await doc.delete(session=current_session())
