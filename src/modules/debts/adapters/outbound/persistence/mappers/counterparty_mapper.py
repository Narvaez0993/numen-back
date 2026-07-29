from uuid import UUID

from src.modules.debts.adapters.outbound.persistence.documents.counterparty_document import (
    CounterpartyDocument,
)
from src.modules.debts.domain.entities.counterparty import Counterparty, name_key


class CounterpartyMapper:
    @staticmethod
    def to_domain(doc: CounterpartyDocument) -> Counterparty:
        return Counterparty(
            id=doc.id,
            user_id=UUID(doc.user_id),
            name=doc.name,
            color=doc.color,
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(counterparty: Counterparty) -> CounterpartyDocument:
        return CounterpartyDocument(
            id=counterparty.id,
            user_id=str(counterparty.user_id),
            name=counterparty.name,
            name_key=name_key(counterparty.name),
            color=counterparty.color,
            created_at=counterparty.created_at,
        )
