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
    source_type: str | None
    source_id: str | None
    destination_type: str | None
    destination_id: str | None
    category_id: str | None
    occurred_on: str
    status: str
    movement_id: str | None


class DebtDraftResponse(BaseModel):
    id: str
    kind: str
    """`new` | `payment`. The card is a different card for each, so a response that
    drops this renders a repayment as a loan — wrong question, wrong options."""
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


class ParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    source: Literal["voice", "text"]


class ParseResponse(BaseModel):
    """Either the draft lists carry what was understood or `clarification` carries a
    question — never both. Two lists because one capture can name several things at
    once, and because lending is not spending: "le presté 50 mil a Andrés" comes back
    as a debt draft, not an expense."""

    drafts: list[DraftResponse]
    debt_drafts: list[DebtDraftResponse] = []
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


class ConfirmDebtDraftRequest(BaseModel):
    """The card's answers; absent means "keep what the agent staged".

    `account_id` sent explicitly as `null` is a real answer — "no money moved" — and
    the truth for a split bill, so it is a decision rather than an omission.
    """

    target_debt_id: str | None = None
    direction: str | None = None
    counterparty_id: str | None = None
    counterparty_name: str | None = None
    amount: int | None = None
    account_id: str | None = None
    due_on: str | None = None
    note: str | None = None


class ConfirmDebtDraftResponse(BaseModel):
    draft: DebtDraftResponse
    debt_id: str
    movement_id: str | None = None
    """Set on an abono. Its presence is what tells the client which undo applies:
    delete this movement, rather than delete the debt."""


class DiscardDebtDraftResponse(BaseModel):
    draft: DebtDraftResponse
