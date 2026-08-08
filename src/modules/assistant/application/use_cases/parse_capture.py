"""One capture: text in → a staged draft out (or one short question).

This is the chat loop's little sibling — same system prompt, same toolset (so
the cached prefix is byte-identical and the margin holds), but capture-shaped:
the first call FORCES `stage_movement_draft`, a second free call lets the model
self-correct or ask, and a forced `respond_with_blocks` closes with the
question when there is one. No chat message is written — the sheet is the quiet
shortcut; the thread stays a conversation.

Money rules mirror the chat's: the registration gate runs before any model
call, a successful stage commits draft + counter atomically, and a
clarification charges nothing (a question is not a captured movement).
"""

from dataclasses import dataclass, replace
from typing import Final

from pydantic import ValidationError as PydanticValidationError

from src.modules.assistant.application.dto.blocks import RespondWithBlocksInput, TextBlock
from src.modules.assistant.application.dto.chat import (
    CounterDTO,
    MessagesCounterDTO,
    UsageOutputDTO,
)
from src.modules.assistant.application.dto.debt_draft import DebtDraftDTO
from src.modules.assistant.application.dto.draft import DraftDTO
from src.modules.assistant.application.dto.parse import (
    ParseCaptureInputDTO,
    ParseCaptureOutputDTO,
)
from src.modules.assistant.application.ports.accounts_reader import AccountsReader
from src.modules.assistant.application.ports.action_log import ActionLog, ActionLogEntry
from src.modules.assistant.application.ports.agent_model import (
    FORCE_ANY_TOOL,
    ZERO_USAGE,
    AgentModel,
    ModelMessage,
    ModelTurn,
    TokenUsage,
    ToolCall,
    ToolResult,
)
from src.modules.assistant.application.ports.categories_reader import CategoriesReader
from src.modules.assistant.application.ports.debt_draft_repository import DebtDraftRepository
from src.modules.assistant.application.ports.draft_repository import DraftRepository
from src.modules.assistant.application.ports.usage_counters import UsageCounters, UsageView
from src.modules.assistant.application.pricing import ModelPricing, PlanLimits
from src.modules.assistant.application.services import prompt_builder
from src.modules.assistant.application.services.prompt_builder import ContextFacts
from src.modules.assistant.application.services.tool_registry import (
    RESPOND_TOOL,
    STAGE_TOOLS,
    ToolContext,
    ToolRegistry,
)
from src.modules.assistant.domain.entities.debt_draft import DebtDraft
from src.modules.assistant.domain.entities.movement_draft import MovementDraft
from src.modules.assistant.domain.errors import (
    AgentProtocolError,
    AgentUnavailableError,
    RegistrationLimitReachedError,
)
from src.modules.assistant.domain.usage import registrations_available
from src.shared.application.ports.unit_of_work import UnitOfWork

_MAX_CALLS: Final[int] = 3


@dataclass
class _Tally:
    usage: TokenUsage = ZERO_USAGE
    calls: int = 0

    def add(self, usage: TokenUsage) -> None:
        self.usage = self.usage.plus(usage)
        self.calls += 1


@dataclass
class ParseCaptureUseCase:
    agent_model: AgentModel
    tool_registry: ToolRegistry
    drafts: DraftRepository
    debt_drafts: DebtDraftRepository
    usage_counters: UsageCounters
    action_log: ActionLog
    unit_of_work: UnitOfWork
    accounts_reader: AccountsReader
    categories_reader: CategoriesReader
    plan_limits: PlanLimits
    pricing: ModelPricing
    model_name: str

    async def execute(self, input_dto: ParseCaptureInputDTO) -> ParseCaptureOutputDTO:
        period = input_dto.today[:7]
        registrations_limit = self.plan_limits.registrations_for(input_dto.tier)
        usage_before = await self.usage_counters.month_usage(input_dto.user_id, period)
        if not registrations_available(usage_before.registrations_used, registrations_limit):
            raise RegistrationLimitReachedError()

        transcript = [
            ModelMessage(
                role="user",
                text=(
                    f"{await self._build_context(input_dto, usage_before, registrations_limit)}"
                    f"\n\n{prompt_builder.capture_instruction(input_dto.language)}"
                    f"\n\n{input_dto.text}"
                ),
            )
        ]

        tally = _Tally()
        try:
            drafts, debt_drafts, clarification = await self._run_loop(
                input_dto, transcript, tally, registrations_limit, usage_before
            )
        except (AgentUnavailableError, AgentProtocolError):
            await self.action_log.record(self._log_entry(input_dto, period, tally, failed=True))
            raise

        # One capture can hold several things, and each one is a registration: the
        # quota counts what the user recorded, not how many times they spoke. A debt
        # counts the same as a movement — it is the same act of capturing.
        consumed = len(drafts) + len(debt_drafts)
        if consumed:
            captured = list(drafts)
            captured_debts = list(debt_drafts)

            async def commit() -> None:
                await self.drafts.save_many(captured)
                await self.debt_drafts.save_many(captured_debts)
                await self.usage_counters.consume(
                    input_dto.user_id, period, registrations=consumed, messages=0
                )

            await self.unit_of_work.atomic(commit)

        await self.action_log.record(self._log_entry(input_dto, period, tally, failed=False))

        return ParseCaptureOutputDTO(
            drafts=[DraftDTO.from_domain(staged) for staged in drafts],
            debt_drafts=[DebtDraftDTO.from_domain(staged) for staged in debt_drafts],
            clarification=clarification,
            usage=UsageOutputDTO(
                registrations=CounterDTO(
                    used=usage_before.registrations_used + consumed, limit=registrations_limit
                ),
                messages=MessagesCounterDTO(
                    used=usage_before.messages_used,
                    limit=self.plan_limits.messages_for(input_dto.tier),
                    grace=self.plan_limits.message_grace,
                ),
            ),
        )

    async def _run_loop(
        self,
        input_dto: ParseCaptureInputDTO,
        transcript: list[ModelMessage],
        tally: _Tally,
        registrations_limit: int,
        usage_before: UsageView,
    ) -> tuple[list[MovementDraft], list[DebtDraft], str | None]:
        system = prompt_builder.system_for(input_dto.language)
        specs = self.tool_registry.specs()
        context = ToolContext(
            user_id=input_dto.user_id,
            currency=input_dto.currency,
            today=input_dto.today,
            registrations_used=usage_before.registrations_used,
            registrations_limit=registrations_limit,
            staged_count=0,
            capture_source=input_dto.source,
        )

        while tally.calls < _MAX_CALLS:
            is_first = tally.calls == 0
            is_last = tally.calls == _MAX_CALLS - 1
            # The first call must stage SOMETHING rather than chat — but which
            # capture it is belongs to the sentence, not to us. Naming the movement
            # tool here is what used to turn "le presté 50 mil a Andrés" into an
            # expense: the model had no legal way to say "this is a debt".
            force = FORCE_ANY_TOOL if is_first else (RESPOND_TOOL if is_last else None)
            turn = await self.agent_model.respond(
                system=system, messages=transcript, tools=specs, force_tool=force
            )
            tally.add(turn.usage)

            final_call = next((c for c in turn.tool_calls if c.name == RESPOND_TOOL), None)
            if final_call is not None:
                return [], [], _clarification_from(final_call, input_dto.language)

            # One capture can hold several movements ("10 mil en café, 5 mil en
            # papitas"), and the model stages them as parallel calls in one turn.
            # Executing only the first would silently drop the rest.
            stage_calls = [call for call in turn.tool_calls if call.name in STAGE_TOOLS]
            if stage_calls:
                staged: list[MovementDraft] = []
                staged_debts: list[DebtDraft] = []
                results: list[ToolResult] = []
                for call in stage_calls:
                    # `staged_count` moves as we go: the quota gate must see
                    # everything staged earlier in this same turn, of either kind.
                    outcome = await self.tool_registry.execute(
                        call,
                        replace(context, staged_count=len(staged) + len(staged_debts)),
                    )
                    if outcome.draft is not None:
                        staged.append(outcome.draft)
                    if outcome.debt_draft is not None:
                        staged_debts.append(outcome.debt_draft)
                    results.append(
                        ToolResult(
                            tool_call_id=call.id,
                            content=outcome.content,
                            is_error=outcome.is_error,
                        )
                    )
                if staged or staged_debts:
                    return staged, staged_debts, None
                transcript.append(_assistant_turn(turn))
                transcript.append(_tool_results_for(turn.tool_calls, results))
                continue

            if turn.tool_calls:
                # Read tools on the free middle call: honest and cheap — answer
                # them and let the forced final call turn it into a question.
                transcript.append(_assistant_turn(turn))
                results = []
                for call in turn.tool_calls:
                    result = await self.tool_registry.execute(call, context)
                    results.append(
                        ToolResult(
                            tool_call_id=call.id, content=result.content, is_error=result.is_error
                        )
                    )
                transcript.append(ModelMessage(role="user", tool_results=tuple(results)))
                continue

            text = turn.text.strip()
            if text:
                return [], [], text[:280]
            transcript.append(_assistant_turn(turn))
            transcript.append(
                ModelMessage(
                    role="user",
                    text="Stage the movement or the debt, or ask your one question.",
                )
            )

        return [], [], prompt_builder.fallback_text(input_dto.language)

    async def _build_context(
        self, input_dto: ParseCaptureInputDTO, usage: UsageView, registrations_limit: int
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
        self, input_dto: ParseCaptureInputDTO, period: str, tally: _Tally, *, failed: bool
    ) -> ActionLogEntry:
        return ActionLogEntry(
            user_id=input_dto.user_id,
            action=f"parse_{input_dto.source}",
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


def _assistant_turn(turn: ModelTurn) -> ModelMessage:
    return ModelMessage(
        role="assistant",
        text=turn.text or None,
        tool_calls=turn.tool_calls,
        provider_state=turn.provider_state,
    )


def _tool_results_for(calls: tuple[ToolCall, ...], executed: list[ToolResult]) -> ModelMessage:
    """Every call in the turn needs a result or the provider rejects the next
    request. The ones we ran carry their real outcome; anything else in the same
    turn is marked unexecuted so the model knows it was skipped, not answered."""
    by_id = {result.tool_call_id: result for result in executed}
    return ModelMessage(
        role="user",
        tool_results=tuple(
            by_id.get(
                call.id,
                ToolResult(
                    tool_call_id=call.id,
                    content='{"error":"not executed"}',
                    is_error=True,
                ),
            )
            for call in calls
        ),
    )


def _clarification_from(final_call: ToolCall, language: str) -> str:
    try:
        parsed = RespondWithBlocksInput.model_validate(final_call.arguments)
    except PydanticValidationError:
        return prompt_builder.fallback_text(language)
    texts = [block.text for block in parsed.blocks if isinstance(block, TextBlock)]
    joined = " ".join(texts).strip()
    return joined[:280] if joined else prompt_builder.fallback_text(language)
