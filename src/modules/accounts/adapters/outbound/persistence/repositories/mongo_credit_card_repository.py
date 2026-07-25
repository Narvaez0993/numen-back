from uuid import UUID

from src.modules.accounts.adapters.outbound.persistence.documents.credit_card_document import (
    CreditCardDocument,
)
from src.modules.accounts.adapters.outbound.persistence.mappers.credit_card_mapper import (
    CreditCardMapper,
)
from src.modules.accounts.domain.entities.credit_card import CreditCard


class MongoCreditCardRepository:
    """Beanie/Mongo implementation of `CreditCardRepository`."""

    async def list_by_user(self, user_id: UUID) -> list[CreditCard]:
        docs = (
            await CreditCardDocument.find(CreditCardDocument.user_id == str(user_id))
            .sort("+created_at")
            .to_list()
        )
        return [CreditCardMapper.to_domain(doc) for doc in docs]

    async def find(self, user_id: UUID, card_id: str) -> CreditCard | None:
        doc = await CreditCardDocument.find_one(
            CreditCardDocument.id == card_id,
            CreditCardDocument.user_id == str(user_id),
        )
        return CreditCardMapper.to_domain(doc) if doc else None

    async def save(self, card: CreditCard) -> None:
        existing = await CreditCardDocument.get(card.id)
        if existing is None:
            await CreditCardMapper.to_document(card).insert()
            return
        existing.name = card.name
        existing.icon = card.icon
        existing.color = card.color
        existing.currency = card.currency
        existing.debt = card.debt
        existing.initial_debt = card.initial_debt
        existing.limit = card.limit
        existing.cutoff_day = card.cutoff_day
        existing.due_day = card.due_day
        await existing.save()

    async def delete(self, user_id: UUID, card_id: str) -> None:
        doc = await CreditCardDocument.find_one(
            CreditCardDocument.id == card_id,
            CreditCardDocument.user_id == str(user_id),
        )
        if doc is not None:
            await doc.delete()
