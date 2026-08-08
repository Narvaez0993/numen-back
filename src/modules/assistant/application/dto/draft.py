from pydantic import BaseModel

from src.modules.assistant.domain.entities.movement_draft import MovementDraft


class DraftDTO(BaseModel):
    """A staged movement as the client reads it — status included, because the
    chat history keeps showing a draft long after it was confirmed or discarded."""

    id: str
    type: str
    description: str
    amount: int
    currency: str
    source_type: str | None
    source_id: str | None
    destination_type: str | None
    destination_id: str | None
    category_id: str | None
    occurred_on: str
    status: str
    movement_id: str | None

    @classmethod
    def from_domain(cls, draft: MovementDraft) -> "DraftDTO":
        return cls(
            id=draft.id,
            type=draft.type,
            description=draft.description,
            amount=draft.amount,
            currency=draft.currency,
            source_type=draft.source_type,
            source_id=draft.source_id,
            destination_type=draft.destination_type,
            destination_id=draft.destination_id,
            category_id=draft.category_id,
            occurred_on=draft.occurred_on,
            status=draft.status,
            movement_id=draft.movement_id,
        )
