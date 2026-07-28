"""One chat turn: quota gate → model loop with tools → atomic commit → cost log.

The order encodes the money rules. The user's message is persisted before the
model runs (what they wrote survives any failure). The model is never called
inside a transaction (a Mongo transaction across 5-20 s of network calls is
not a transaction). Drafts, the assistant message and the counter increment
commit together — so a charged-but-unanswered turn cannot exist. The cost log
runs last and best-effort: losing a row costs analytics, never money.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import ValidationError as PydanticValidationError

from src.modules.assistant.application.dto.blocks import (
    DraftRefBlock,
    LlmBlock,
    RespondWithBlocksInput,
    TextBlock,
)
from src.modules.assistant.application.dto.chat import (
    ChatMessageDTO,
    ChatTurnOutputDTO,
    CounterDTO,
    MessagesCounterDTO,
    SendChatInputDTO,
    UsageOutputDTO,
)
from src.modules.assistant.application.ports.accounts_reader import AccountsReader
from src.modules.assistant.application.ports.action_log import ActionLog, ActionLogEntry
from src.modules.assistant.application.ports.agent_model import (
    ZERO_USAGE,
    AgentModel,
    ModelMessage,
    TokenUsage,
    ToolResult,
)
from src.modules.assistant.application.ports.categories_reader import CategoriesReader
from src.modules.assistant.application.ports.chat_message_repository import (
    ChatMessageRepository,
    StoredChatMessage,
)
from src.modules.assistant.application.ports.draft_repository import DraftRepository
from src.modules.assistant.application.ports.usage_counters import UsageCounters, UsageView
from src.modules.assistant.application.pricing import ModelPricing, PlanLimits
from src.modules.assistant.application.services import prompt_builder
from src.modules.assistant.application.services.block_hydration import hydrate_blocks
from src.modules.assistant.application.services.prompt_builder import ContextFacts
from src.modules.assistant.application.services.tool_registry import (
    RESPOND_TOOL,
    ToolContext,
    ToolRegistry,
)
from src.modules.assistant.domain.entities.movement_draft import MovementDraft
from src.modules.assistant.domain.errors import (
    AgentProtocolError,
    AgentUnavailableError,
    DuplicateMessageError,
)
from src.modules.assistant.domain.usage import Consumption, derive_consumption, ensure_can_chat
from src.shared.application.ports.unit_of_work import UnitOfWork


@dataclass
class _Tally:
    """Mutable across the loop so a mid-flight provider failure still logs the
    tokens the successful calls already spent."""

    usage: TokenUsage = ZERO_USAGE
    calls: int = 0

    def add(self, usage: TokenUsage) -> None:
        self.usage = self.usage.plus(usage)
        self.calls += 1


@dataclass(frozen=True)
class _LoopOutcome:
    blocks: tuple[LlmBlock, ...]
    staged: tuple[MovementDraft, ...]
    read_tools_used: bool
    charged: bool
    """False when we answered with a canned line (refusal / protocol fallback):
    our failure to answer is never billed to the user."""


@dataclass
class SendChatMessageUseCase:
    agent_model: AgentModel
    tool_registry: ToolRegistry
    chat_messages: ChatMessageRepository
    drafts: DraftRepository
    usage_counters: UsageCounters
    action_log: ActionLog
    unit_of_work: UnitOfWork
    accounts_reader: AccountsReader
    categories_reader: CategoriesReader
    plan_limits: PlanLimits
    pricing: ModelPricing
    model_name: str
    history_window: int
    max_tool_iterations: int

    async def execute(self, input_dto: SendChatInputDTO) -> ChatTurnOutputDTO:
        period = input_dto.today[:7]
        registrations_limit = self.plan_limits.registrations_for(input_dto.tier)
        messages_limit = self.plan_limits.messages_for(input_dto.tier)

        usage_before = await self.usage_counters.month_usage(input_dto.user_id, period)
        ensure_can_chat(usage_before.messages_used, messages_limit, self.plan_limits.message_grace)

        if input_dto.client_message_id is not None:
            seen = await self.chat_messages.find_by_client_id(
                input_dto.user_id, input_dto.client_message_id
            )
            if seen is not None:
                raise DuplicateMessageError()

        history = await self.chat_messages.recent(input_dto.user_id, self.history_window)
        await self.chat_messages.append(
            StoredChatMessage(
                id=str(uuid4()),
                user_id=input_dto.user_id,
                role="user",
                blocks=({"type": "text", "text": input_dto.text},),
                client_message_id=input_dto.client_message_id,
                created_at=datetime.now(UTC),
            )
        )

        context = await self._build_context(input_dto, usage_before, registrations_limit)
        transcript = _render_history(history)
        transcript.append(ModelMessage(role="user", text=f"{context}\n\n{input_dto.text}"))

        tally = _Tally()
        try:
            outcome = await self._run_loop(
                input_dto,
                transcript,
                tally,
                registrations_used=usage_before.registrations_used,
                registrations_limit=registrations_limit,
            )
        except (AgentUnavailableError, AgentProtocolError):
            await self.action_log.record(self._log_entry(input_dto, period, tally, failed=True))
            raise

        kept_ids = {block.draft_id for block in outcome.blocks if isinstance(block, DraftRefBlock)}
        drafts_to_persist = (
            [draft for draft in outcome.staged if draft.id in kept_ids] if outcome.charged else []
        )
        has_data_blocks = any(
            block.type in {"stat", "chart", "navigate"} for block in outcome.blocks
        )
        consumption = (
            derive_consumption(
                len(drafts_to_persist),
                read_tools_used=outcome.read_tools_used,
                has_data_blocks=has_data_blocks,
            )
            if outcome.charged
            else Consumption(registrations=0, messages=0)
        )

        assistant_message = StoredChatMessage(
            id=str(uuid4()),
            user_id=input_dto.user_id,
            role="assistant",
            blocks=tuple(block.model_dump(mode="json") for block in outcome.blocks),
            client_message_id=None,
            created_at=datetime.now(UTC),
        )

        async def commit() -> None:
            if drafts_to_persist:
                await self.drafts.save_many(drafts_to_persist)
            await self.chat_messages.append(assistant_message)
            if consumption.registrations or consumption.messages:
                await self.usage_counters.consume(
                    input_dto.user_id,
                    period,
                    registrations=consumption.registrations,
                    messages=consumption.messages,
                )

        await self.unit_of_work.atomic(commit)
        await self.action_log.record(self._log_entry(input_dto, period, tally, failed=False))

        drafts_by_id = {draft.id: draft for draft in drafts_to_persist}
        return ChatTurnOutputDTO(
            message=ChatMessageDTO(
                id=assistant_message.id,
                role="assistant",
                blocks=hydrate_blocks(assistant_message.blocks, drafts_by_id),
                created_at=assistant_message.created_at,
            ),
            usage=UsageOutputDTO(
                registrations=CounterDTO(
                    used=usage_before.registrations_used + consumption.registrations,
                    limit=registrations_limit,
                ),
                messages=MessagesCounterDTO(
                    used=usage_before.messages_used + consumption.messages,
                    limit=messages_limit,
                    grace=self.plan_limits.message_grace,
                ),
            ),
        )

    async def _run_loop(
        self,
        input_dto: SendChatInputDTO,
        transcript: list[ModelMessage],
        tally: _Tally,
        *,
        registrations_used: int,
        registrations_limit: int,
    ) -> _LoopOutcome:
        system = prompt_builder.system_for(input_dto.language)
        specs = self.tool_registry.specs()
        staged: list[MovementDraft] = []
        read_tools_used = False
        retried_blocks = False

        while tally.calls < self.max_tool_iterations:
            force = RESPOND_TOOL if tally.calls == self.max_tool_iterations - 1 else None
            turn = await self.agent_model.respond(
                system=system, messages=transcript, tools=specs, force_tool=force
            )
            tally.add(turn.usage)

            if turn.stop_reason == "refusal":
                return _loop_fallback(
                    prompt_builder.refusal_text(input_dto.language), staged, read_tools_used
                )

            final_call = next((c for c in turn.tool_calls if c.name == RESPOND_TOOL), None)
            if final_call is not None:
                try:
                    parsed = RespondWithBlocksInput.model_validate(final_call.arguments)
                    _ensure_draft_refs_exist(parsed.blocks, {draft.id for draft in staged})
                    return _LoopOutcome(
                        blocks=tuple(parsed.blocks),
                        staged=tuple(staged),
                        read_tools_used=read_tools_used,
                        charged=True,
                    )
                except (PydanticValidationError, ValueError) as exc:
                    if retried_blocks:
                        break
                    retried_blocks = True
                    transcript.append(
                        ModelMessage(
                            role="assistant",
                            text=turn.text or None,
                            tool_calls=turn.tool_calls,
                            provider_state=turn.provider_state,
                        )
                    )
                    transcript.append(
                        ModelMessage(
                            role="user",
                            tool_results=tuple(
                                ToolResult(
                                    tool_call_id=call.id,
                                    content=json.dumps(
                                        {"error": str(exc)}
                                        if call.id == final_call.id
                                        else {"error": "fix respond_with_blocks first"}
                                    ),
                                    is_error=True,
                                )
                                for call in turn.tool_calls
                            ),
                        )
                    )
                    continue

            if not turn.tool_calls:
                # `end_turn` with plain text: tolerated, wrapped as a text block.
                text = turn.text.strip()
                if text:
                    return _LoopOutcome(
                        blocks=(TextBlock(type="text", text=text[:2000]),),
                        staged=tuple(staged),
                        read_tools_used=read_tools_used,
                        charged=True,
                    )
                return _loop_fallback(
                    prompt_builder.fallback_text(input_dto.language), staged, read_tools_used
                )

            transcript.append(
                ModelMessage(
                    role="assistant",
                    text=turn.text or None,
                    tool_calls=turn.tool_calls,
                    provider_state=turn.provider_state,
                )
            )
            results: list[ToolResult] = []
            for call in turn.tool_calls:
                context = ToolContext(
                    user_id=input_dto.user_id,
                    currency=input_dto.currency,
                    today=input_dto.today,
                    registrations_used=registrations_used,
                    registrations_limit=registrations_limit,
                    staged_count=len(staged),
                )
                result = await self.tool_registry.execute(call, context)
                if result.draft is not None:
                    staged.append(result.draft)
                if result.is_read:
                    read_tools_used = True
                results.append(
                    ToolResult(
                        tool_call_id=call.id, content=result.content, is_error=result.is_error
                    )
                )
            transcript.append(ModelMessage(role="user", tool_results=tuple(results)))

        return _loop_fallback(
            prompt_builder.fallback_text(input_dto.language), staged, read_tools_used
        )

    async def _build_context(
        self, input_dto: SendChatInputDTO, usage: UsageView, registrations_limit: int
    ) -> str:
        accounts = await self.accounts_reader.overview(input_dto.user_id, input_dto.currency)
        categories = await self.categories_reader.all(input_dto.user_id)
        facts = ContextFacts(
            today=input_dto.today,
            currency=input_dto.currency,
            objective=input_dto.objective,
            registrations_used=usage.registrations_used,
            registrations_limit=registrations_limit,
            messages_used=usage.messages_used,
            messages_limit=self.plan_limits.messages_for(input_dto.tier),
        )
        return prompt_builder.build_context(facts, accounts, categories)

    def _log_entry(
        self, input_dto: SendChatInputDTO, period: str, tally: _Tally, *, failed: bool
    ) -> ActionLogEntry:
        return ActionLogEntry(
            user_id=input_dto.user_id,
            action="chat",
            model=self.model_name,
            calls=tally.calls,
            input_tokens=tally.usage.input_tokens,
            output_tokens=tally.usage.output_tokens,
            cache_read_tokens=tally.usage.cache_read_tokens,
            cache_write_tokens=tally.usage.cache_write_tokens,
            cost_usd=self.pricing.cost_usd(tally.usage),
            period=period,
            failed=failed,
        )


def _loop_fallback(text: str, staged: list[MovementDraft], read_tools_used: bool) -> _LoopOutcome:
    return _LoopOutcome(
        blocks=(TextBlock(type="text", text=text),),
        staged=tuple(staged),
        read_tools_used=read_tools_used,
        charged=False,
    )


def _render_history(messages: tuple[StoredChatMessage, ...]) -> list[ModelMessage]:
    """Past turns as plain text — tool transcripts are never replayed (the
    provider rejects stale tool_use/tool_result adjacency, and they add nothing:
    the data they carried is stale by definition)."""
    rendered: list[ModelMessage] = []
    for message in messages:
        if message.role == "user":
            text = next(
                (str(b.get("text", "")) for b in message.blocks if b.get("type") == "text"), ""
            )
            if text:
                rendered.append(ModelMessage(role="user", text=text))
        else:
            rendered.append(
                ModelMessage(
                    role="assistant", text=json.dumps(list(message.blocks), ensure_ascii=False)
                )
            )
    return rendered


def _ensure_draft_refs_exist(blocks: list[LlmBlock], known_ids: set[str]) -> None:
    for block in blocks:
        if isinstance(block, DraftRefBlock) and block.draft_id not in known_ids:
            raise ValueError(f"draft block references unknown draft_id {block.draft_id!r}")
