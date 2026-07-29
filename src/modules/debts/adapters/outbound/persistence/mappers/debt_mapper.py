from typing import cast
from uuid import UUID

from src.modules.debts.adapters.outbound.persistence.documents.debt_document import (
    DebtDocument,
    PaymentEntry,
)
from src.modules.debts.domain.entities.debt import Debt, Direction, Payment


class DebtMapper:
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
            payments=tuple(
                Payment(id=p.id, amount=p.amount, paid_on=p.paid_on, note=p.note)
                for p in doc.payments
            ),
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
            payments=[
                PaymentEntry(id=p.id, amount=p.amount, paid_on=p.paid_on, note=p.note)
                for p in debt.payments
            ],
            created_at=debt.created_at,
        )
