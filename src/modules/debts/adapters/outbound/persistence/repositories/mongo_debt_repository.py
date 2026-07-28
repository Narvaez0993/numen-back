from uuid import UUID

from src.modules.debts.adapters.outbound.persistence.documents.debt_document import (
    DebtDocument,
)
from src.modules.debts.adapters.outbound.persistence.mappers.debt_mapper import DebtMapper
from src.modules.debts.domain.entities.debt import Debt
from src.shared.adapters.outbound.persistence.mongo import current_session


class MongoDebtRepository:
    """Beanie/Mongo implementation of `DebtRepository`. Every read is tenant-scoped."""

    async def list_by_user(self, user_id: UUID) -> list[Debt]:
        docs = await DebtDocument.find({"user_id": str(user_id)}).to_list()
        return [DebtMapper.to_domain(doc) for doc in docs]

    async def list_by_event(self, user_id: UUID, event_id: str) -> list[Debt]:
        docs = await DebtDocument.find({"user_id": str(user_id), "event_id": event_id}).to_list()
        return [DebtMapper.to_domain(doc) for doc in docs]

    async def find(self, user_id: UUID, debt_id: str) -> Debt | None:
        doc = await DebtDocument.find_one(
            DebtDocument.id == debt_id,
            DebtDocument.user_id == str(user_id),
        )
        return DebtMapper.to_domain(doc) if doc else None

    async def save(self, debt: Debt) -> None:
        session = current_session()
        existing = await DebtDocument.get(debt.id, session=session)
        if existing is None:
            await DebtMapper.to_document(debt).insert(session=session)
            return
        # Who it is between is identity and never changes; what it says can.
        fresh = DebtMapper.to_document(debt)
        existing.amount = fresh.amount
        existing.currency = fresh.currency
        existing.due_on = fresh.due_on
        existing.note = fresh.note
        existing.payments = fresh.payments
        await existing.save(session=session)

    async def delete(self, user_id: UUID, debt_id: str) -> None:
        doc = await DebtDocument.find_one(
            DebtDocument.id == debt_id,
            DebtDocument.user_id == str(user_id),
        )
        if doc is not None:
            await doc.delete(session=current_session())
