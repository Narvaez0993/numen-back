from pydantic import BaseModel

from src.modules.assistant.domain.entities.debt_draft import DebtDraft


class DebtDraftDTO(BaseModel):
    """A staged debt as the client reads it — status included, because the chat
    history keeps showing a draft long after it was confirmed or discarded."""

    id: str
    kind: str
    """`new` | `payment` — the card asks different questions for each."""
    target_debt_id: str | None
    direction: str
    counterparty_id: str | None
    counterparty_name: str
    amount: int
    currency: str
    account_id: str | None
    due_on: str | None
    note: str | None
    status: str
    debt_id: str | None

    @classmethod
    def from_domain(cls, draft: DebtDraft) -> "DebtDraftDTO":
        return cls(
            id=draft.id,
            kind=draft.kind,
            target_debt_id=draft.target_debt_id,
            direction=draft.direction,
            counterparty_id=draft.counterparty_id,
            counterparty_name=draft.counterparty_name,
            amount=draft.amount,
            currency=draft.currency,
            account_id=draft.account_id,
            due_on=draft.due_on,
            note=draft.note,
            status=draft.status,
            debt_id=draft.debt_id,
        )
