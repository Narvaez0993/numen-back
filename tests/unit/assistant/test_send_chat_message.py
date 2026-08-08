"""The chat loop end to end against a scripted model — no network anywhere.

What these tests pin down is the money order: what gets persisted, what gets
charged, and that a failing provider can never charge or lose the user's words.
"""

import json
from collections.abc import Sequence
from typing import Any

import pytest

from src.modules.assistant.application.dto.chat import SendChatInputDTO
from src.modules.assistant.application.ports.agent_model import ModelMessage, ToolCall
from src.modules.assistant.application.use_cases.send_chat_message import SendChatMessageUseCase
from src.modules.assistant.domain.errors import (
    AgentUnavailableError,
    ChatLimitReachedError,
    DuplicateMessageError,
)

from .fakes import (
    ACCOUNT_ID,
    PLAN_LIMITS,
    PRICING,
    TODAY,
    USER_ID,
    FailingAgentModel,
    FakeAccountsReader,
    FakeActionLog,
    FakeAgentModel,
    FakeCategoriesReader,
    FakeChatMessages,
    FakeDebtDrafts,
    FakeDrafts,
    FakeUnitOfWork,
    FakeUsageCounters,
    last_tool_result,
    registry,
    respond_call,
    turn,
)


def use_case(
    model: FakeAgentModel | FailingAgentModel,
    *,
    chat_messages: FakeChatMessages | None = None,
    drafts: FakeDrafts | None = None,
    usage: FakeUsageCounters | None = None,
    action_log: FakeActionLog | None = None,
    max_tool_iterations: int = 6,
) -> tuple[SendChatMessageUseCase, FakeChatMessages, FakeDrafts, FakeUsageCounters, FakeActionLog]:
    chat_messages = chat_messages or FakeChatMessages()
    drafts = drafts or FakeDrafts()
    usage = usage or FakeUsageCounters()
    action_log = action_log or FakeActionLog()
    case = SendChatMessageUseCase(
        agent_model=model,
        tool_registry=registry(),
        chat_messages=chat_messages,
        drafts=drafts,
        debt_drafts=FakeDebtDrafts(),
        usage_counters=usage,
        action_log=action_log,
        unit_of_work=FakeUnitOfWork(),
        accounts_reader=FakeAccountsReader(),
        categories_reader=FakeCategoriesReader(),
        plan_limits=PLAN_LIMITS,
        pricing=PRICING,
        model_name="fake-model",
        history_window=24,
        max_tool_iterations=max_tool_iterations,
    )
    return case, chat_messages, drafts, usage, action_log


def send_input(text: str = "¿cómo voy este mes?", **overrides: Any) -> SendChatInputDTO:
    base: dict[str, Any] = {
        "user_id": USER_ID,
        "currency": "COP",
        "tier": "free",
        "language": "es",
        "objective": "ahorrar",
        "today": TODAY,
        "text": text,
    }
    base.update(overrides)
    return SendChatInputDTO(**base)


def summary_then_blocks() -> list[Any]:
    return [
        turn(
            tool_calls=(ToolCall(id="c1", name="get_month_summary", arguments={}),),
        ),
        turn(
            tool_calls=(
                respond_call(
                    [
                        {"type": "text", "text": "Llevas $1.250.000 gastados."},
                        {
                            "type": "stat",
                            "label": "Gastado",
                            "value": "$1.250.000",
                            "amount": 1_250_000,
                        },
                    ]
                ),
            ),
        ),
    ]


@pytest.mark.asyncio
async def test_a_question_reads_tools_and_costs_one_message() -> None:
    case, messages, drafts, usage, log = use_case(FakeAgentModel(summary_then_blocks()))

    output = await case.execute(send_input())

    assert [m.role for m in messages.appended] == ["user", "assistant"]
    assert output.message.blocks[0].type == "text"
    assert usage.consumed == [{"registrations": 0, "messages": 1}]
    assert output.usage.messages.used == 1
    assert drafts.saved == []
    assert log.entries[0].failed is False
    assert log.entries[0].calls == 2
    assert log.entries[0].cost_usd > 0


@pytest.mark.asyncio
async def test_a_capture_stages_a_draft_and_costs_one_registration() -> None:
    def final(messages: Sequence[ModelMessage]) -> Any:
        draft_id = last_tool_result(messages)["draft_id"]
        return turn(
            tool_calls=(
                respond_call(
                    [
                        {"type": "text", "text": "Listo, confírmalo."},
                        {"type": "draft", "draft_id": draft_id},
                    ]
                ),
            ),
        )

    script = [
        turn(
            tool_calls=(
                ToolCall(
                    id="c1",
                    name="stage_movement_draft",
                    arguments={
                        "type": "expense",
                        "amount": "25000",
                        "description": "Almuerzo",
                        "source_id": ACCOUNT_ID,
                    },
                ),
            ),
        ),
        final,
    ]
    case, _, drafts, usage, _ = use_case(FakeAgentModel(script))

    output = await case.execute(send_input("pagué 25 mil de almuerzo con nequi"))

    assert len(drafts.saved) == 1
    assert drafts.saved[0].amount == 25_000
    assert drafts.saved[0].status == "pending"
    assert usage.consumed == [{"registrations": 1, "messages": 0}]
    hydrated = [b for b in output.message.blocks if b.type == "draft"]
    assert len(hydrated) == 1
    assert hydrated[0].draft.id == drafts.saved[0].id  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_a_mixed_turn_costs_one_and_one() -> None:
    def final(messages: Sequence[ModelMessage]) -> Any:
        for message in reversed(messages):
            for result in message.tool_results:
                payload = json.loads(result.content)
                if "draft_id" in payload:
                    return turn(
                        tool_calls=(
                            respond_call(
                                [
                                    {"type": "text", "text": "Guardado va, y vas así:"},
                                    {"type": "draft", "draft_id": payload["draft_id"]},
                                    {
                                        "type": "stat",
                                        "label": "Mes",
                                        "value": "$1.250.000",
                                        "amount": 1_250_000,
                                    },
                                ]
                            ),
                        ),
                    )
        raise AssertionError("draft result not found")

    script = [
        turn(
            tool_calls=(
                ToolCall(
                    id="c1",
                    name="stage_movement_draft",
                    arguments={
                        "type": "expense",
                        "amount": "25000",
                        "description": "Almuerzo",
                        "source_id": ACCOUNT_ID,
                    },
                ),
                ToolCall(id="c2", name="get_month_summary", arguments={}),
            ),
        ),
        final,
    ]
    case, _, drafts, usage, _ = use_case(FakeAgentModel(script))

    await case.execute(send_input("pagué 25 mil, ¿cómo voy?"))

    assert len(drafts.saved) == 1
    assert usage.consumed == [{"registrations": 1, "messages": 1}]


@pytest.mark.asyncio
async def test_a_staged_draft_the_answer_ignores_is_dropped() -> None:
    script = [
        turn(
            tool_calls=(
                ToolCall(
                    id="c1",
                    name="stage_movement_draft",
                    arguments={
                        "type": "expense",
                        "amount": "25000",
                        "description": "Almuerzo",
                        "source_id": ACCOUNT_ID,
                    },
                ),
            ),
        ),
        turn(tool_calls=(respond_call([{"type": "text", "text": "¿De qué cuenta salió?"}]),)),
    ]
    case, _, drafts, usage, _ = use_case(FakeAgentModel(script))

    await case.execute(send_input())

    assert drafts.saved == []
    assert usage.consumed == [{"registrations": 0, "messages": 1}]


@pytest.mark.asyncio
async def test_invalid_blocks_get_one_retry_then_a_free_fallback() -> None:
    bad = respond_call([{"type": "navigate", "label": "x", "route": "https://evil"}])
    script = [turn(tool_calls=(bad,)), turn(tool_calls=(bad,))]
    case, messages, _, usage, log = use_case(FakeAgentModel(script))

    output = await case.execute(send_input())

    assert usage.consumed == []  # our failure is never billed
    assert output.message.blocks[0].type == "text"
    assert "No logré" in output.message.blocks[0].text  # type: ignore[union-attr]
    assert [m.role for m in messages.appended] == ["user", "assistant"]
    assert log.entries[0].calls == 2


@pytest.mark.asyncio
async def test_a_refusal_is_a_canned_line_and_costs_nothing() -> None:
    case, _, _, usage, _ = use_case(FakeAgentModel([turn(stop_reason="refusal")]))

    output = await case.execute(send_input())

    assert usage.consumed == []
    assert output.message.blocks[0].type == "text"


@pytest.mark.asyncio
async def test_plain_end_turn_text_is_tolerated_and_charged() -> None:
    case, _, _, usage, _ = use_case(
        FakeAgentModel([turn(text="Hola, soy tu agente.", stop_reason="end_turn")])
    )

    output = await case.execute(send_input("hola"))

    assert output.message.blocks[0].type == "text"
    assert usage.consumed == [{"registrations": 0, "messages": 1}]


@pytest.mark.asyncio
async def test_the_last_iteration_forces_the_terminal_tool() -> None:
    read = turn(tool_calls=(ToolCall(id="c", name="get_month_summary", arguments={}),))
    final = turn(tool_calls=(respond_call([{"type": "text", "text": "listo"}]),))
    model = FakeAgentModel([read, final])
    case, _, _, _, _ = use_case(model, max_tool_iterations=2)

    await case.execute(send_input())

    assert model.requests[0]["force_tool"] is None
    assert model.requests[1]["force_tool"] == "respond_with_blocks"


@pytest.mark.asyncio
async def test_a_dead_provider_charges_nothing_and_keeps_the_user_message() -> None:
    case, messages, drafts, usage, log = use_case(FailingAgentModel(AgentUnavailableError()))

    with pytest.raises(AgentUnavailableError):
        await case.execute(send_input())

    assert [m.role for m in messages.appended] == ["user"]
    assert drafts.saved == []
    assert usage.consumed == []
    assert log.entries[0].failed is True


@pytest.mark.asyncio
async def test_a_mid_loop_failure_still_logs_the_tokens_already_spent() -> None:
    read = turn(tool_calls=(ToolCall(id="c", name="get_month_summary", arguments={}),))
    case, _, _, usage, log = use_case(FailingAgentModel(AgentUnavailableError(), after=[read]))

    with pytest.raises(AgentUnavailableError):
        await case.execute(send_input())

    assert usage.consumed == []
    assert log.entries[0].failed is True
    assert log.entries[0].calls == 1
    assert log.entries[0].input_tokens == 1000


@pytest.mark.asyncio
async def test_the_gate_closes_past_the_grace_before_any_model_call() -> None:
    model = FakeAgentModel([])
    case, messages, _, _, _ = use_case(model, usage=FakeUsageCounters(messages_used=13))

    with pytest.raises(ChatLimitReachedError):
        await case.execute(send_input())

    assert model.requests == []
    assert messages.appended == []


@pytest.mark.asyncio
async def test_inside_the_grace_window_the_turn_is_served() -> None:
    case, _, _, usage, _ = use_case(
        FakeAgentModel(summary_then_blocks()), usage=FakeUsageCounters(messages_used=12)
    )

    output = await case.execute(send_input())

    assert output.usage.messages.used == 13
    assert usage.consumed == [{"registrations": 0, "messages": 1}]


@pytest.mark.asyncio
async def test_a_repeated_client_message_id_is_a_conflict() -> None:
    chat_messages = FakeChatMessages()
    case, _, _, _, _ = use_case(FakeAgentModel(summary_then_blocks()), chat_messages=chat_messages)
    await case.execute(send_input(client_message_id="cmid-1"))

    retry_case, _, _, _, _ = use_case(FakeAgentModel([]), chat_messages=chat_messages)
    with pytest.raises(DuplicateMessageError):
        await retry_case.execute(send_input(client_message_id="cmid-1"))


@pytest.mark.asyncio
async def test_the_context_rides_in_the_last_user_message() -> None:
    model = FakeAgentModel(summary_then_blocks())
    case, _, _, _, _ = use_case(model)

    await case.execute(send_input("¿cómo voy?"))

    last_user = model.requests[0]["messages"][-1]
    assert "[context]" in last_user.text
    assert "Nequi" in last_user.text
    assert "¿cómo voy?" in last_user.text
    assert "es" not in model.requests[0]["system"][:2]  # system starts with the ES identity
    assert model.requests[0]["system"].startswith("Eres")


@pytest.mark.asyncio
async def test_blocks_written_as_text_are_salvaged_and_rendered() -> None:
    # The model sometimes mimics the history's JSON instead of calling the tool.
    mimic = json.dumps(
        [
            {"type": "text", "text": "Este mes tus gastos se concentran en dos categorías."},
            {"type": "stat", "label": "Suscripciones", "value": "$50.000", "amount": 50000},
            {"type": "navigate", "label": "Ver movimientos", "route": "/movements"},
        ]
    )
    case, _, _, usage, _ = use_case(FakeAgentModel([turn(text=mimic, stop_reason="end_turn")]))

    output = await case.execute(send_input("¿en qué se me va la plata?"))

    kinds = [block.type for block in output.message.blocks]
    assert kinds == ["text", "stat", "navigate"]
    assert usage.consumed == [{"registrations": 0, "messages": 1}]


@pytest.mark.asyncio
async def test_the_tool_argument_object_written_as_text_is_salvaged_too() -> None:
    mimic = json.dumps({"blocks": [{"type": "text", "text": "hola"}]})
    case, _, _, _, _ = use_case(FakeAgentModel([turn(text=mimic, stop_reason="end_turn")]))

    output = await case.execute(send_input())

    assert [block.type for block in output.message.blocks] == ["text"]


@pytest.mark.asyncio
async def test_almost_block_json_retries_instead_of_showing_raw_json() -> None:
    broken = '[{"type": "stat", "label": "x"}]'  # missing required `value`
    good = turn(tool_calls=(respond_call([{"type": "text", "text": "listo"}]),))
    model = FakeAgentModel([turn(text=broken, stop_reason="end_turn"), good])
    case, _, _, _, _ = use_case(model)

    output = await case.execute(send_input())

    assert len(model.requests) == 2
    text_block = output.message.blocks[0]
    assert text_block.type == "text"
    assert "listo" in text_block.text  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_ordinary_prose_still_lands_as_a_text_block() -> None:
    case, _, _, usage, _ = use_case(
        FakeAgentModel([turn(text="Hola, ¿en qué te ayudo?", stop_reason="end_turn")])
    )

    output = await case.execute(send_input("hola"))

    assert output.message.blocks[0].type == "text"
    assert usage.consumed == [{"registrations": 0, "messages": 1}]
