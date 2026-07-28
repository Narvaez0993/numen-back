from fastapi import APIRouter, Depends, Query

from src.modules.assistant.adapters.inbound.http.schemas import (
    ChatHistoryResponse,
    ChatRequest,
    ChatTurnResponse,
    ConfirmDraftRequest,
    ConfirmDraftResponse,
    DiscardDraftResponse,
    UsageResponse,
)
from src.modules.assistant.application.dto.chat import HistoryInputDTO, SendChatInputDTO
from src.modules.assistant.application.dto.draft_commands import (
    ConfirmDraftInputDTO,
    DiscardDraftInputDTO,
)
from src.modules.assistant.application.use_cases.confirm_draft import ConfirmDraftUseCase
from src.modules.assistant.application.use_cases.discard_draft import DiscardDraftUseCase
from src.modules.assistant.application.use_cases.get_chat_history import GetChatHistoryUseCase
from src.modules.assistant.application.use_cases.get_usage import GetUsageUseCase, UsageInputDTO
from src.modules.assistant.application.use_cases.send_chat_message import SendChatMessageUseCase
from src.shared.adapters.inbound.http.dependencies import CallerContext, get_caller
from src.shared.adapters.inbound.http.today import resolve_today

router = APIRouter(prefix="/assistant", tags=["assistant"])


def _depends_send_chat() -> SendChatMessageUseCase:
    from src.core.di.container import get_container

    return get_container().send_chat_message_use_case


def _depends_history() -> GetChatHistoryUseCase:
    from src.core.di.container import get_container

    return get_container().get_chat_history_use_case


def _depends_confirm() -> ConfirmDraftUseCase:
    from src.core.di.container import get_container

    return get_container().confirm_draft_use_case


def _depends_discard() -> DiscardDraftUseCase:
    from src.core.di.container import get_container

    return get_container().discard_draft_use_case


def _depends_usage() -> GetUsageUseCase:
    from src.core.di.container import get_container

    return get_container().get_assistant_usage_use_case


@router.post("/chat", response_model=ChatTurnResponse)
async def send_chat_message(
    body: ChatRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: SendChatMessageUseCase = Depends(_depends_send_chat),
) -> ChatTurnResponse:
    output = await use_case.execute(
        SendChatInputDTO(
            user_id=caller.user_id,
            currency=caller.currency,
            tier=caller.tier,
            language=caller.language,
            objective=caller.objective,
            today=resolve_today(today),
            text=body.text,
            client_message_id=body.client_message_id,
        )
    )
    return ChatTurnResponse(**output.model_dump())


@router.get("/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    before: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    caller: CallerContext = Depends(get_caller),
    use_case: GetChatHistoryUseCase = Depends(_depends_history),
) -> ChatHistoryResponse:
    output = await use_case.execute(
        HistoryInputDTO(user_id=caller.user_id, before=before, limit=limit)
    )
    return ChatHistoryResponse(**output.model_dump())


@router.post("/drafts/{draft_id}/confirm", response_model=ConfirmDraftResponse)
async def confirm_draft(
    draft_id: str,
    body: ConfirmDraftRequest,
    caller: CallerContext = Depends(get_caller),
    use_case: ConfirmDraftUseCase = Depends(_depends_confirm),
) -> ConfirmDraftResponse:
    output = await use_case.execute(
        ConfirmDraftInputDTO(
            user_id=caller.user_id,
            draft_id=draft_id,
            type=body.type,
            description=body.description,
            amount=body.amount,
            source_type=body.source_type,
            source_id=body.source_id,
            destination_type=body.destination_type,
            destination_id=body.destination_id,
            category_id=body.category_id,
            occurred_on=body.occurred_on,
            clear_category="category_id" in body.model_fields_set and body.category_id is None,
        )
    )
    return ConfirmDraftResponse(**output.model_dump())


@router.post("/drafts/{draft_id}/discard", response_model=DiscardDraftResponse)
async def discard_draft(
    draft_id: str,
    caller: CallerContext = Depends(get_caller),
    use_case: DiscardDraftUseCase = Depends(_depends_discard),
) -> DiscardDraftResponse:
    output = await use_case.execute(DiscardDraftInputDTO(user_id=caller.user_id, draft_id=draft_id))
    return DiscardDraftResponse(**output.model_dump())


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: GetUsageUseCase = Depends(_depends_usage),
) -> UsageResponse:
    output = await use_case.execute(
        UsageInputDTO(user_id=caller.user_id, tier=caller.tier, today=resolve_today(today))
    )
    return UsageResponse(**output.model_dump())
