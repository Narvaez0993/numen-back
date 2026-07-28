from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.assistant.application.dto.blocks import ApiBlock


class SendChatInputDTO(BaseModel):
    user_id: UUID
    currency: str
    tier: str
    language: str
    objective: str | None
    today: str
    text: str
    client_message_id: str | None = None


class HistoryInputDTO(BaseModel):
    user_id: UUID
    before: str | None = None
    limit: int = 50


class ChatMessageDTO(BaseModel):
    id: str
    role: str
    blocks: list[ApiBlock]
    created_at: datetime


class CounterDTO(BaseModel):
    used: int
    limit: int


class MessagesCounterDTO(CounterDTO):
    grace: int
    """Messages served past the limit before the hard gate — the nudge window."""


class UsageOutputDTO(BaseModel):
    registrations: CounterDTO
    messages: MessagesCounterDTO


class ChatTurnOutputDTO(BaseModel):
    message: ChatMessageDTO
    usage: UsageOutputDTO


class ChatHistoryOutputDTO(BaseModel):
    messages: list[ChatMessageDTO]
    next_before: str | None
