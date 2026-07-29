from uuid import UUID

from pydantic import BaseModel

from src.modules.assistant.application.dto.draft import DraftDTO


class ConfirmDraftInputDTO(BaseModel):
    """Overrides are the user's edits from the confirm sheet; `None` means keep
    what the agent staged. `amount` is already in minor units — the client's
    form speaks minor units everywhere (cash-register style input)."""

    user_id: UUID
    draft_id: str
    type: str | None = None
    description: str | None = None
    amount: int | None = None
    source_type: str | None = None
    source_id: str | None = None
    destination_type: str | None = None
    destination_id: str | None = None
    category_id: str | None = None
    occurred_on: str | None = None
    clear_category: bool = False
    """Distinguishes "leave the category" (None) from "remove it" (True)."""


class DiscardDraftInputDTO(BaseModel):
    user_id: UUID
    draft_id: str


class ConfirmDraftOutputDTO(BaseModel):
    draft: DraftDTO
    movement_id: str


class DiscardDraftOutputDTO(BaseModel):
    draft: DraftDTO
