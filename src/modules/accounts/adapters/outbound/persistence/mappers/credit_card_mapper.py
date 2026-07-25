from uuid import UUID

from src.modules.accounts.adapters.outbound.persistence.documents.credit_card_document import (
    CreditCardDocument,
)
from src.modules.accounts.domain.entities.credit_card import CreditCard


class CreditCardMapper:
    @staticmethod
    def to_domain(doc: CreditCardDocument) -> CreditCard:
        return CreditCard(
            id=doc.id,
            user_id=UUID(doc.user_id),
            name=doc.name,
            icon=doc.icon,
            color=doc.color,
            currency=doc.currency,
            debt=doc.debt,
            initial_debt=doc.initial_debt,
            limit=doc.limit,
            cutoff_day=doc.cutoff_day,
            due_day=doc.due_day,
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(card: CreditCard) -> CreditCardDocument:
        return CreditCardDocument(
            id=card.id,
            user_id=str(card.user_id),
            name=card.name,
            icon=card.icon,
            color=card.color,
            currency=card.currency,
            debt=card.debt,
            initial_debt=card.initial_debt,
            limit=card.limit,
            cutoff_day=card.cutoff_day,
            due_day=card.due_day,
            created_at=card.created_at,
        )
