from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.modules.assistant.application.dto.blocks import ApiBlock
from src.modules.assistant.application.dto.insights import InsightDTO
from src.modules.assistant.application.dto.outputs import AgentOutputDTO

# The block union is imported, not re-declared: it IS the contract, and a
# hand-copied twin here is exactly the kind of drift blocks.py exists to kill.
# Same story for insights and agent outputs below.


class FeedResponse(BaseModel):
    insights: list[InsightDTO]
    outputs: list[AgentOutputDTO]
    unseen_count: int


class OutputsListResponse(BaseModel):
    outputs: list[AgentOutputDTO]


class ApplyPlayRequest(BaseModel):
    account_id: str | None = Field(default=None, min_length=1, max_length=64)


class DismissInsightRequest(BaseModel):
    key: str = Field(min_length=1, max_length=120)


class ChatRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    client_message_id: str | None = Field(default=None, min_length=1, max_length=64)


class CounterResponse(BaseModel):
    used: int
    limit: int


class MessagesCounterResponse(CounterResponse):
    grace: int


class UsageResponse(BaseModel):
    registrations: CounterResponse
    messages: MessagesCounterResponse


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    blocks: list[ApiBlock]
    created_at: datetime


class ChatTurnResponse(BaseModel):
    message: ChatMessageResponse
    usage: UsageResponse


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageResponse]
    next_before: str | None


class DraftResponse(BaseModel):
    id: str
    type: str
    description: str
    amount: int
    currency: str
    source_type: str
    source_id: str
    destination_type: str | None
    destination_id: str | None
    category_id: str | None
    occurred_on: str
    status: str
    movement_id: str | None


class ParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    source: Literal["voice", "text"]


class ParseResponse(BaseModel):
    """Exactly one of `draft` / `clarification` is set."""

    draft: DraftResponse | None
    clarification: str | None
    usage: UsageResponse


class ConfirmDraftRequest(BaseModel):
    """Every field optional: absent means "keep what the agent staged". A
    `category_id` explicitly sent as `null` clears it (the edit form sends the
    whole picture, so null is a decision, not an omission)."""

    type: str | None = None
    description: str | None = None
    amount: int | None = None
    source_type: str | None = None
    source_id: str | None = None
    destination_type: str | None = None
    destination_id: str | None = None
    category_id: str | None = None
    occurred_on: str | None = None


class ConfirmDraftResponse(BaseModel):
    draft: DraftResponse
    movement_id: str


class DiscardDraftResponse(BaseModel):
    draft: DraftResponse
