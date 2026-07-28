from uuid import UUID

from pydantic import BaseModel

from src.modules.assistant.application.dto.chat import UsageOutputDTO
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
    """Exactly one of `draft` / `clarification` is set: either the agent
    understood a movement, or it has one short question."""

    draft: DraftDTO | None
    clarification: str | None
    usage: UsageOutputDTO
