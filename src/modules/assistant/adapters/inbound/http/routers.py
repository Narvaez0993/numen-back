from fastapi import APIRouter, Depends, Query

from src.modules.assistant.adapters.inbound.http.schemas import (
    ApplyPlayRequest,
    ChatHistoryResponse,
    ChatRequest,
    ChatTurnResponse,
    ConfirmDebtDraftRequest,
    ConfirmDebtDraftResponse,
    ConfirmDraftRequest,
    ConfirmDraftResponse,
    DiscardDebtDraftResponse,
    DiscardDraftResponse,
    DismissInsightRequest,
    FeedResponse,
    OutputsListResponse,
    ParseRequest,
    ParseResponse,
    UsageResponse,
)
from src.modules.assistant.application.dto.chat import HistoryInputDTO, SendChatInputDTO
from src.modules.assistant.application.dto.debt_draft_commands import (
    ConfirmDebtDraftInputDTO,
    DiscardDebtDraftInputDTO,
)
from src.modules.assistant.application.dto.draft_commands import (
    ConfirmDraftInputDTO,
    DiscardDraftInputDTO,
)
from src.modules.assistant.application.dto.outputs import AgentOutputDTO
from src.modules.assistant.application.dto.parse import ParseCaptureInputDTO
from src.modules.assistant.application.use_cases.apply_play import (
    ApplyPlayInputDTO,
    ApplyPlayUseCase,
)
from src.modules.assistant.application.use_cases.confirm_debt_draft import (
    ConfirmDebtDraftUseCase,
)
from src.modules.assistant.application.use_cases.confirm_draft import ConfirmDraftUseCase
from src.modules.assistant.application.use_cases.discard_debt_draft import (
    DiscardDebtDraftUseCase,
)
from src.modules.assistant.application.use_cases.discard_draft import DiscardDraftUseCase
from src.modules.assistant.application.use_cases.dismiss_insight import (
    DismissInsightInputDTO,
    DismissInsightUseCase,
)
from src.modules.assistant.application.use_cases.dismiss_output import (
    DismissOutputInputDTO,
    DismissOutputUseCase,
)
from src.modules.assistant.application.use_cases.get_chat_history import GetChatHistoryUseCase
from src.modules.assistant.application.use_cases.get_feed import (
    FeedInputDTO,
    GetAssistantFeedUseCase,
)
from src.modules.assistant.application.use_cases.get_output import (
    GetOutputInputDTO,
    GetOutputUseCase,
)
from src.modules.assistant.application.use_cases.get_usage import GetUsageUseCase, UsageInputDTO
from src.modules.assistant.application.use_cases.list_outputs import (
    ListOutputsInputDTO,
    ListOutputsUseCase,
)
from src.modules.assistant.application.use_cases.mark_output_read import (
    MarkOutputReadInputDTO,
    MarkOutputReadUseCase,
)
from src.modules.assistant.application.use_cases.parse_capture import ParseCaptureUseCase
from src.modules.assistant.application.use_cases.send_chat_message import SendChatMessageUseCase
from src.shared.adapters.inbound.http.dependencies import CallerContext, get_caller
from src.shared.adapters.inbound.http.today import resolve_today

router = APIRouter(prefix="/assistant", tags=["assistant"])


def _depends_send_chat() -> SendChatMessageUseCase:
    from src.core.di.container import get_container

    return get_container().send_chat_message_use_case


def _depends_feed() -> GetAssistantFeedUseCase:
    from src.core.di.container import get_container

    return get_container().get_assistant_feed_use_case


def _depends_dismiss_insight() -> DismissInsightUseCase:
    from src.core.di.container import get_container

    return get_container().dismiss_insight_use_case


def _depends_apply_play() -> ApplyPlayUseCase:
    from src.core.di.container import get_container

    return get_container().apply_play_use_case


def _depends_list_outputs() -> ListOutputsUseCase:
    from src.core.di.container import get_container

    return get_container().list_outputs_use_case


def _depends_get_output() -> GetOutputUseCase:
    from src.core.di.container import get_container

    return get_container().get_output_use_case


def _depends_mark_output_read() -> MarkOutputReadUseCase:
    from src.core.di.container import get_container

    return get_container().mark_output_read_use_case


def _depends_dismiss_output() -> DismissOutputUseCase:
    from src.core.di.container import get_container

    return get_container().dismiss_output_use_case


def _depends_parse() -> ParseCaptureUseCase:
    from src.core.di.container import get_container

    return get_container().parse_capture_use_case


def _depends_history() -> GetChatHistoryUseCase:
    from src.core.di.container import get_container

    return get_container().get_chat_history_use_case


def _depends_confirm() -> ConfirmDraftUseCase:
    from src.core.di.container import get_container

    return get_container().confirm_draft_use_case


def _depends_confirm_debt() -> ConfirmDebtDraftUseCase:
    from src.core.di.container import get_container

    return get_container().confirm_debt_draft_use_case


def _depends_discard_debt() -> DiscardDebtDraftUseCase:
    from src.core.di.container import get_container

    return get_container().discard_debt_draft_use_case


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


@router.post("/parse", response_model=ParseResponse)
async def parse_capture(
    body: ParseRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: ParseCaptureUseCase = Depends(_depends_parse),
) -> ParseResponse:
    output = await use_case.execute(
        ParseCaptureInputDTO(
            user_id=caller.user_id,
            currency=caller.currency,
            tier=caller.tier,
            language=caller.language,
            objective=caller.objective,
            today=resolve_today(today),
            text=body.text,
            source=body.source,
        )
    )
    return ParseResponse(**output.model_dump())


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


@router.post("/debt-drafts/{draft_id}/confirm", response_model=ConfirmDebtDraftResponse)
async def confirm_debt_draft(
    draft_id: str,
    body: ConfirmDebtDraftRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: ConfirmDebtDraftUseCase = Depends(_depends_confirm_debt),
) -> ConfirmDebtDraftResponse:
    """Turns the staged debt into a real one — person resolved (or created) and, when
    an account is named, the loan leaving it as a real transfer."""
    output = await use_case.execute(
        ConfirmDebtDraftInputDTO(
            user_id=caller.user_id,
            draft_id=draft_id,
            today=resolve_today(today),
            target_debt_id=body.target_debt_id,
            direction=body.direction,
            counterparty_id=body.counterparty_id,
            counterparty_name=body.counterparty_name,
            amount=body.amount,
            account_id=body.account_id,
            clear_account="account_id" in body.model_fields_set and body.account_id is None,
            due_on=body.due_on,
            note=body.note,
        )
    )
    return ConfirmDebtDraftResponse(**output.model_dump())


@router.post("/debt-drafts/{draft_id}/discard", response_model=DiscardDebtDraftResponse)
async def discard_debt_draft(
    draft_id: str,
    caller: CallerContext = Depends(get_caller),
    use_case: DiscardDebtDraftUseCase = Depends(_depends_discard_debt),
) -> DiscardDebtDraftResponse:
    output = await use_case.execute(
        DiscardDebtDraftInputDTO(user_id=caller.user_id, draft_id=draft_id)
    )
    return DiscardDebtDraftResponse(**output.model_dump())


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: GetAssistantFeedUseCase = Depends(_depends_feed),
) -> FeedResponse:
    output = await use_case.execute(
        FeedInputDTO(user_id=caller.user_id, currency=caller.currency, today=resolve_today(today))
    )
    return FeedResponse(**output.model_dump())


@router.post("/insights/dismiss", status_code=204)
async def dismiss_insight(
    body: DismissInsightRequest,
    caller: CallerContext = Depends(get_caller),
    use_case: DismissInsightUseCase = Depends(_depends_dismiss_insight),
) -> None:
    await use_case.execute(DismissInsightInputDTO(user_id=caller.user_id, key=body.key))


@router.get("/outputs", response_model=OutputsListResponse)
async def list_outputs(
    kind: str = Query(default="monthly_summary", pattern="^(monthly_summary|weekly_review)$"),
    limit: int = Query(default=24, ge=1, le=48),
    caller: CallerContext = Depends(get_caller),
    use_case: ListOutputsUseCase = Depends(_depends_list_outputs),
) -> OutputsListResponse:
    output = await use_case.execute(
        ListOutputsInputDTO(user_id=caller.user_id, kind=kind, limit=limit)
    )
    return OutputsListResponse(**output.model_dump())


@router.get("/outputs/{output_id}", response_model=AgentOutputDTO)
async def get_output(
    output_id: str,
    caller: CallerContext = Depends(get_caller),
    use_case: GetOutputUseCase = Depends(_depends_get_output),
) -> AgentOutputDTO:
    return await use_case.execute(GetOutputInputDTO(user_id=caller.user_id, output_id=output_id))


@router.post("/outputs/{output_id}/read", response_model=AgentOutputDTO)
async def mark_output_read(
    output_id: str,
    caller: CallerContext = Depends(get_caller),
    use_case: MarkOutputReadUseCase = Depends(_depends_mark_output_read),
) -> AgentOutputDTO:
    return await use_case.execute(
        MarkOutputReadInputDTO(user_id=caller.user_id, output_id=output_id)
    )


@router.post("/outputs/{output_id}/dismiss", response_model=AgentOutputDTO)
async def dismiss_output(
    output_id: str,
    caller: CallerContext = Depends(get_caller),
    use_case: DismissOutputUseCase = Depends(_depends_dismiss_output),
) -> AgentOutputDTO:
    return await use_case.execute(
        DismissOutputInputDTO(user_id=caller.user_id, output_id=output_id)
    )


@router.post(
    "/outputs/{output_id}/plays/{play_id}/apply",
    response_model=AgentOutputDTO,
)
async def apply_play(
    output_id: str,
    play_id: str,
    body: ApplyPlayRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: ApplyPlayUseCase = Depends(_depends_apply_play),
) -> AgentOutputDTO:
    return await use_case.execute(
        ApplyPlayInputDTO(
            user_id=caller.user_id,
            tier=caller.tier,
            currency=caller.currency,
            today=resolve_today(today),
            output_id=output_id,
            play_id=play_id,
            account_id=body.account_id,
        )
    )


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
