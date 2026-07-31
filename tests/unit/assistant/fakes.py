"""Duck-typed fakes for the assistant's ports, with spies for assertions.

`FakeAgentModel` scripts the model: each entry is a `ModelTurn` or a callable
`(messages) -> ModelTurn`, so a script can read the draft_id a tool minted —
exactly what the real model does with a tool result.
"""

import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from src.modules.assistant.application.ports.accounts_reader import (
    AccountsView,
    AccountView,
    CreditCardView,
)
from src.modules.assistant.application.ports.action_log import ActionLogEntry
from src.modules.assistant.application.ports.agent_model import (
    ZERO_USAGE,
    ModelMessage,
    ModelTurn,
    TokenUsage,
    ToolCall,
    ToolSpec,
)
from src.modules.assistant.application.ports.agent_output_repository import (
    AgentOutputAlreadyExistsError,
)
from src.modules.assistant.application.ports.budgets_reader import BudgetsView
from src.modules.assistant.application.ports.categories_reader import CategoryView
from src.modules.assistant.application.ports.chat_message_repository import StoredChatMessage
from src.modules.assistant.application.ports.debts_reader import DebtsView
from src.modules.assistant.application.ports.goals_reader import GoalView
from src.modules.assistant.application.ports.movement_recorder import RecordedMovement
from src.modules.assistant.application.ports.movements_reader import (
    DaySpendView,
    MerchantView,
    MovementView,
    PeriodSummaryView,
)
from src.modules.assistant.application.ports.subscriptions_reader import (
    SubscriptionsView,
    UpcomingChargeView,
)
from src.modules.assistant.application.ports.usage_counters import UsageView
from src.modules.assistant.application.pricing import ModelPricing, PlanLimits
from src.modules.assistant.application.services.tool_registry import ToolRegistry
from src.modules.assistant.domain.entities.agent_output import (
    MONTHLY_SUMMARY,
    PLAY_PROPOSED,
    AgentOutput,
    Play,
)
from src.modules.assistant.domain.entities.movement_draft import MovementDraft

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
TODAY = "2026-07-28"
CURRENCY = "COP"
ACCOUNT_ID = "acc-nequi"
CARD_ID = "card-visa"
CATEGORY_ID = "comida"
INCOME_CATEGORY_ID = "salario"

PLAN_LIMITS = PlanLimits(
    registrations_free=60,
    registrations_plus=300,
    messages_free=10,
    messages_plus=300,
    message_grace=3,
)
PRICING = ModelPricing(input_usd_per_mtok=3.0, output_usd_per_mtok=15.0)
SOME_USAGE = TokenUsage(
    input_tokens=1000, output_tokens=200, cache_read_tokens=500, cache_write_tokens=100
)

TurnScript = ModelTurn | Callable[[Sequence[ModelMessage]], ModelTurn]


def turn(
    *,
    text: str = "",
    tool_calls: tuple[ToolCall, ...] = (),
    stop_reason: str = "tool_use",
    usage: TokenUsage = SOME_USAGE,
) -> ModelTurn:
    return ModelTurn(
        text=text,
        tool_calls=tool_calls,
        stop_reason=stop_reason,  # type: ignore[arg-type]
        usage=usage,
        model="fake-model",
    )


def respond_call(blocks: list[dict[str, Any]], call_id: str = "call-final") -> ToolCall:
    return ToolCall(id=call_id, name="respond_with_blocks", arguments={"blocks": blocks})


def last_tool_result(messages: Sequence[ModelMessage]) -> dict[str, Any]:
    for message in reversed(messages):
        if message.tool_results:
            payload: dict[str, Any] = json.loads(message.tool_results[-1].content)
            return payload
    raise AssertionError("no tool result in transcript")


class FakeAgentModel:
    def __init__(self, script: list[TurnScript]) -> None:
        self.script = list(script)
        self.requests: list[dict[str, Any]] = []

    async def respond(
        self,
        *,
        system: str,
        messages: Sequence[ModelMessage],
        tools: Sequence[ToolSpec],
        force_tool: str | None = None,
    ) -> ModelTurn:
        self.requests.append(
            {
                "system": system,
                "messages": list(messages),
                "tools": [t.name for t in tools],
                "force_tool": force_tool,
            }
        )
        if not self.script:
            raise AssertionError("FakeAgentModel script exhausted")
        entry = self.script.pop(0)
        return entry(messages) if callable(entry) else entry


class FailingAgentModel:
    def __init__(self, error: Exception, after: list[TurnScript] | None = None) -> None:
        self.error = error
        self.before = FakeAgentModel(after or [])

    async def respond(
        self,
        *,
        system: str,
        messages: Sequence[ModelMessage],
        tools: Sequence[ToolSpec],
        force_tool: str | None = None,
    ) -> ModelTurn:
        if self.before.script:
            return await self.before.respond(
                system=system, messages=messages, tools=tools, force_tool=force_tool
            )
        raise self.error


class FakeChatMessages:
    def __init__(self) -> None:
        self.appended: list[StoredChatMessage] = []

    async def append(self, message: StoredChatMessage) -> None:
        self.appended.append(message)

    async def recent(self, user_id: UUID, limit: int) -> tuple[StoredChatMessage, ...]:
        return tuple(self.appended[-limit:])

    async def before(
        self, user_id: UUID, before_id: str | None, limit: int
    ) -> tuple[StoredChatMessage, ...]:
        messages = self.appended
        if before_id is not None:
            ids = [m.id for m in messages]
            messages = messages[: ids.index(before_id)] if before_id in ids else []
        return tuple(messages[-limit:])

    async def find_by_client_id(
        self, user_id: UUID, client_message_id: str
    ) -> StoredChatMessage | None:
        return next((m for m in self.appended if m.client_message_id == client_message_id), None)


class FakeDrafts:
    def __init__(self, drafts: list[MovementDraft] | None = None) -> None:
        self.by_id: dict[str, MovementDraft] = {d.id: d for d in drafts or []}
        self.saved: list[MovementDraft] = []

    async def save(self, draft: MovementDraft) -> None:
        self.by_id[draft.id] = draft
        self.saved.append(draft)

    async def save_many(self, drafts: Sequence[MovementDraft]) -> None:
        for draft in drafts:
            await self.save(draft)

    async def find(self, user_id: UUID, draft_id: str) -> MovementDraft | None:
        draft = self.by_id.get(draft_id)
        return draft if draft is not None and draft.user_id == user_id else None

    async def find_many(self, user_id: UUID, draft_ids: Sequence[str]) -> tuple[MovementDraft, ...]:
        return tuple(
            d for i in draft_ids if (d := self.by_id.get(i)) is not None and d.user_id == user_id
        )


class FakeUsageCounters:
    def __init__(self, registrations_used: int = 0, messages_used: int = 0) -> None:
        self.view = UsageView(registrations_used=registrations_used, messages_used=messages_used)
        self.consumed: list[dict[str, int]] = []

    async def month_usage(self, user_id: UUID, period: str) -> UsageView:
        return self.view

    async def consume(
        self, user_id: UUID, period: str, *, registrations: int, messages: int
    ) -> None:
        self.consumed.append({"registrations": registrations, "messages": messages})


class FakeActionLog:
    def __init__(self) -> None:
        self.entries: list[ActionLogEntry] = []

    async def record(self, entry: ActionLogEntry) -> None:
        self.entries.append(entry)


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0

    async def atomic(self, operation: Callable[[], Awaitable[Any]]) -> Any:
        self.commits += 1
        return await operation()


ACCOUNTS_VIEW = AccountsView(
    currency=CURRENCY,
    net_balance=8_000_000,
    debit_total=7_500_000,
    cash_total=500_000,
    card_debt_total=1_200_000,
    accounts=(AccountView(id=ACCOUNT_ID, name="Nequi", kind="bank", balance=7_500_000),),
    credit_cards=(CreditCardView(id=CARD_ID, name="Visa", debt=1_200_000, limit=5_000_000),),
)

CATEGORIES = (
    CategoryView(id=CATEGORY_ID, name="Comida", flow="expense"),
    CategoryView(id=INCOME_CATEGORY_ID, name="Salario", flow="income"),
)


class FakeAccountsReader:
    async def overview(self, user_id: UUID, currency: str) -> AccountsView:
        return ACCOUNTS_VIEW


class FakeCategoriesReader:
    async def all(self, user_id: UUID) -> tuple[CategoryView, ...]:
        return CATEGORIES


class FakeMovementsReader:
    def __init__(self) -> None:
        self.summary_calls: list[tuple[str, str]] = []

    async def summary(self, user_id: UUID, date_from: str, date_to: str) -> PeriodSummaryView:
        self.summary_calls.append((date_from, date_to))
        return PeriodSummaryView(
            date_from=date_from,
            date_to=date_to,
            expense_total=1_250_000,
            income_total=4_000_000,
            count=12,
            by_category=(),
        )

    async def recent(self, user_id: UUID, limit: int) -> tuple[MovementView, ...]:
        return ()

    async def top_merchants(
        self, user_id: UUID, date_from: str, date_to: str, limit: int
    ) -> tuple[MerchantView, ...]:
        return ()

    async def spend_by_day(
        self, user_id: UUID, date_from: str, date_to: str
    ) -> tuple[DaySpendView, ...]:
        return ()


class FakeBudgetsReader:
    async def snapshot(self, user_id: UUID, currency: str, today: str) -> BudgetsView:
        return BudgetsView(period=today[:7], days_left=4, month=None, categories=())


class FakeGoalsReader:
    async def snapshot(self, user_id: UUID, currency: str, today: str) -> tuple[GoalView, ...]:
        return ()


class FakeDebtsReader:
    async def snapshot(self, user_id: UUID, currency: str, today: str) -> DebtsView:
        return DebtsView(i_owe_total=0, owed_to_me_total=0, debts=())


class FakeSubscriptionsReader:
    async def subscriptions(self, user_id: UUID, currency: str, today: str) -> SubscriptionsView:
        return SubscriptionsView(monthly_total=0, yearly_total=0, subscriptions=())

    async def upcoming_charges(
        self, user_id: UUID, currency: str, date_from: str, date_to: str
    ) -> tuple[UpcomingChargeView, ...]:
        return ()


class FakeMovementRecorder:
    def __init__(self) -> None:
        self.recorded: list[dict[str, Any]] = []

    async def record(self, **kwargs: Any) -> RecordedMovement:
        self.recorded.append(kwargs)
        return RecordedMovement(movement_id=f"mov-{len(self.recorded)}")


def registry() -> ToolRegistry:
    return ToolRegistry(
        accounts=FakeAccountsReader(),
        movements=FakeMovementsReader(),
        budgets=FakeBudgetsReader(),
        goals=FakeGoalsReader(),
        debts=FakeDebtsReader(),
        subscriptions=FakeSubscriptionsReader(),
        categories=FakeCategoriesReader(),
    )


def draft(**overrides: Any) -> MovementDraft:
    base: dict[str, Any] = {
        "user_id": USER_ID,
        "currency": CURRENCY,
        "type": "expense",
        "description": "Almuerzo",
        "amount": 25_000,
        "source_type": "account",
        "source_id": ACCOUNT_ID,
        "destination_type": None,
        "destination_id": None,
        "category_id": CATEGORY_ID,
        "occurred_on": TODAY,
        "created_at": datetime(2026, 7, 28, 12, 0, 0, tzinfo=UTC),
    }
    base.update(overrides)
    return MovementDraft.stage(**base)


def stored_message(role: str = "user", text: str = "hola") -> StoredChatMessage:
    return StoredChatMessage(
        id=str(uuid4()),
        user_id=USER_ID,
        role=role,
        blocks=({"type": "text", "text": text},),
        client_message_id=None,
        created_at=datetime(2026, 7, 28, 11, 0, 0, tzinfo=UTC),
    )


class FakeAgentOutputRepository:
    """In-memory `AgentOutputRepository` honoring the conditional-write semantics:
    a transition whose `from_status` no longer holds returns None, like Mongo."""

    def __init__(self) -> None:
        self.outputs: dict[str, AgentOutput] = {}

    async def add(self, output: AgentOutput) -> None:
        duplicate = any(
            o.user_id == output.user_id and o.kind == output.kind and o.period == output.period
            for o in self.outputs.values()
        )
        if duplicate:
            raise AgentOutputAlreadyExistsError()
        self.outputs[output.id] = output

    async def find(self, user_id: UUID, output_id: str) -> AgentOutput | None:
        found = self.outputs.get(output_id)
        return found if found and found.user_id == user_id else None

    async def find_by_period(self, user_id: UUID, kind: str, period: str) -> AgentOutput | None:
        return next(
            (
                o
                for o in self.outputs.values()
                if o.user_id == user_id and o.kind == kind and o.period == period
            ),
            None,
        )

    async def latest(self, user_id: UUID, kind: str, limit: int) -> tuple[AgentOutput, ...]:
        mine = [o for o in self.outputs.values() if o.user_id == user_id and o.kind == kind]
        mine.sort(key=lambda o: o.created_at, reverse=True)
        return tuple(mine[:limit])

    async def mark_read(self, user_id: UUID, output_id: str, at: datetime) -> AgentOutput | None:
        found = await self.find(user_id, output_id)
        if found is None:
            return None
        if found.read_at is None:
            found = replace(found, read_at=at)
            self.outputs[output_id] = found
        return found

    async def dismiss(self, user_id: UUID, output_id: str, at: datetime) -> AgentOutput | None:
        found = await self.find(user_id, output_id)
        if found is None:
            return None
        if found.dismissed_at is None:
            found = replace(found, dismissed_at=at)
            self.outputs[output_id] = found
        return found

    async def transition_play(
        self,
        user_id: UUID,
        output_id: str,
        play_id: str,
        *,
        from_status: str,
        to_status: str,
        result_id: str | None = None,
        failure_code: str | None = None,
        applied_at: datetime | None = None,
    ) -> AgentOutput | None:
        found = await self.find(user_id, output_id)
        if found is None:
            return None
        target = found.play(play_id)
        if target is None or target.status != from_status:
            return None
        moved = replace(
            target,
            status=to_status,
            result_id=result_id if result_id is not None else target.result_id,
            failure_code=failure_code if failure_code is not None else target.failure_code,
            applied_at=applied_at if applied_at is not None else target.applied_at,
        )
        plays = tuple(moved if p.id == play_id else p for p in found.plays)
        updated = replace(found, plays=plays)
        self.outputs[output_id] = updated
        return updated


def play(**overrides: Any) -> Play:
    base: dict[str, Any] = {
        "id": "play-1",
        "action": "set_category_cap",
        "params": {"category_id": CATEGORY_ID, "category_name": "Comida", "target": 400_000},
        "text": "Ponle un techo de $400.000 a comida",
        "status": PLAY_PROPOSED,
        "result_id": None,
        "failure_code": None,
        "applied_at": None,
    }
    base.update(overrides)
    return Play(**base)


def agent_output(**overrides: Any) -> AgentOutput:
    base: dict[str, Any] = {
        "id": str(uuid4()),
        "user_id": USER_ID,
        "kind": MONTHLY_SUMMARY,
        "period": "2026-07",
        "payload": {"slides": []},
        "plays": (play(),),
        "created_at": datetime(2026, 8, 1, 6, 0, 0, tzinfo=UTC),
        "read_at": None,
        "dismissed_at": None,
    }
    base.update(overrides)
    return AgentOutput(**base)


ZERO = ZERO_USAGE
