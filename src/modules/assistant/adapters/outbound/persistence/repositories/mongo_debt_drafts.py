from collections.abc import Sequence
from uuid import UUID

from src.modules.assistant.adapters.outbound.persistence.documents.debt_draft_document import (
    DebtDraftDocument,
)
from src.modules.assistant.adapters.outbound.persistence.mappers.debt_draft_mapper import (
    DebtDraftMapper,
)
from src.modules.assistant.domain.entities.debt_draft import DebtDraft
from src.shared.adapters.outbound.persistence.mongo import current_session


class MongoDebtDraftRepository:
    """Beanie/Mongo implementation of `DebtDraftRepository`."""

    async def save(self, draft: DebtDraft) -> None:
        session = current_session()
        existing = await DebtDraftDocument.get(draft.id, session=session)
        if existing is None:
            await DebtDraftMapper.to_document(draft).insert(session=session)
            return
        fresh = DebtDraftMapper.to_document(draft)
        existing.direction = fresh.direction
        existing.counterparty_id = fresh.counterparty_id
        existing.counterparty_name = fresh.counterparty_name
        existing.amount = fresh.amount
        existing.account_id = fresh.account_id
        existing.due_on = fresh.due_on
        existing.note = fresh.note
        existing.status = fresh.status
        existing.debt_id = fresh.debt_id
        await existing.save(session=session)

    async def save_many(self, drafts: Sequence[DebtDraft]) -> None:
        for draft in drafts:
            await self.save(draft)

    async def find(self, user_id: UUID, draft_id: str) -> DebtDraft | None:
        doc = await DebtDraftDocument.find_one(
            DebtDraftDocument.id == draft_id,
            DebtDraftDocument.user_id == str(user_id),
        )
        return DebtDraftMapper.to_domain(doc) if doc else None

    async def find_many(self, user_id: UUID, draft_ids: Sequence[str]) -> tuple[DebtDraft, ...]:
        docs = await DebtDraftDocument.find(
            {"user_id": str(user_id), "_id": {"$in": list(draft_ids)}}
        ).to_list()
        return tuple(DebtDraftMapper.to_domain(doc) for doc in docs)
