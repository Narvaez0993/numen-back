from uuid import UUID

from pydantic import BaseModel

from src.modules.assistant.application.dto.chat import UsageOutputDTO
from src.modules.assistant.application.dto.debt_draft import DebtDraftDTO
from src.modules.assistant.application.dto.draft import DraftDTO


class ParseCaptureInputDTO(BaseModel):
    user_id: UUID
    currency: str
    tier: str
    language: str
    objective: str | None
    today: str
    text: str
    source: str
    """`voice` | `text` — where the words came from; stamped on the draft."""


class ParseCaptureOutputDTO(BaseModel):
    """Either the agent understood something, or it has one short question — never
    both. Both lists exist because one breath can hold several captures ("10 mil en
    café, 5 mil en papitas"), and because lending is not spending: "le presté 50 mil
    a Andrés" is a debt draft, not an expense. Both empty means it asked instead."""

    drafts: list[DraftDTO]
    debt_drafts: list[DebtDraftDTO] = []
    clarification: str | None
    notice: str | None = None
    """Set when the capture understood SOME of what was said and lost the rest —
    partial success, which used to be reported as total."""
    usage: UsageOutputDTO
