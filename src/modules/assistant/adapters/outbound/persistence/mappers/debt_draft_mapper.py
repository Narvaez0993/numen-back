from uuid import UUID

from src.modules.assistant.adapters.outbound.persistence.documents.debt_draft_document import (
    DebtDraftDocument,
)
from src.modules.assistant.domain.entities.debt_draft import DebtDraft


class DebtDraftMapper:
    @staticmethod
    def to_domain(doc: DebtDraftDocument) -> DebtDraft:
        return DebtDraft(
            id=doc.id,
            user_id=UUID(doc.user_id),
            currency=doc.currency,
            kind=doc.kind,
            target_debt_id=doc.target_debt_id,
            direction=doc.direction,
            counterparty_id=doc.counterparty_id,
            counterparty_name=doc.counterparty_name,
            amount=doc.amount,
            account_id=doc.account_id,
            due_on=doc.due_on,
            note=doc.note,
            status=doc.status,
            debt_id=doc.debt_id,
            created_at=doc.created_at,
            captured_via=doc.captured_via,
        )

    @staticmethod
    def to_document(draft: DebtDraft) -> DebtDraftDocument:
        return DebtDraftDocument(
            id=draft.id,
            user_id=str(draft.user_id),
            currency=draft.currency,
            kind=draft.kind,
            target_debt_id=draft.target_debt_id,
            direction=draft.direction,
            counterparty_id=draft.counterparty_id,
            counterparty_name=draft.counterparty_name,
            amount=draft.amount,
            account_id=draft.account_id,
            due_on=draft.due_on,
            note=draft.note,
            status=draft.status,
            debt_id=draft.debt_id,
            created_at=draft.created_at,
            captured_via=draft.captured_via,
        )
