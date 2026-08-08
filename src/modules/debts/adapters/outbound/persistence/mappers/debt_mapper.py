from typing import cast
from uuid import UUID

from src.modules.debts.adapters.outbound.persistence.documents.debt_document import (
    DebtDocument,
)
from src.modules.debts.domain.entities.debt import Debt, Direction


class DebtMapper:
    """The stored debt is the agreement only.

    Repayments used to be embedded here. They are transfers now, read back through
    `SettlementReader`, so this mapper deliberately neither reads nor writes them —
    a stored copy is exactly the second source of truth the move was meant to kill.
    """

    @staticmethod
    def to_domain(doc: DebtDocument) -> Debt:
        return Debt(
            id=doc.id,
            user_id=UUID(doc.user_id),
            direction=cast(Direction, doc.direction),
            counterparty_id=doc.counterparty_id,
            amount=doc.amount,
            currency=doc.currency,
            due_on=doc.due_on,
            note=doc.note,
            event_id=doc.event_id,
            written_off_on=doc.written_off_on,
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(debt: Debt) -> DebtDocument:
        return DebtDocument(
            id=debt.id,
            user_id=str(debt.user_id),
            direction=debt.direction,
            counterparty_id=debt.counterparty_id,
            amount=debt.amount,
            currency=debt.currency,
            due_on=debt.due_on,
            note=debt.note,
            event_id=debt.event_id,
            written_off_on=debt.written_off_on,
            created_at=debt.created_at,
        )
