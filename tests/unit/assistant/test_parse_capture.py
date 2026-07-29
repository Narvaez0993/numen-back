"""The capture mini-loop: one forced call in the happy path, one honest
question when the text is ambiguous, and the registration gate before any
model call. Money rules mirror the chat's."""

import pytest

from src.modules.assistant.application.dto.parse import ParseCaptureInputDTO
from src.modules.assistant.application.ports.agent_model import ToolCall
from src.modules.assistant.application.use_cases.parse_capture import ParseCaptureUseCase
from src.modules.assistant.domain.errors import RegistrationLimitReachedError

from .fakes import (
    ACCOUNT_ID,
    PLAN_LIMITS,
    PRICING,
    TODAY,
    USER_ID,
    FakeAccountsReader,
    FakeActionLog,
    FakeAgentModel,
    FakeCategoriesReader,
    FakeDrafts,
    FakeUnitOfWork,
    FakeUsageCounters,
    registry,
    respond_call,
    turn,
)


def use_case(
    model: FakeAgentModel,
    *,
    usage: FakeUsageCounters | None = None,
) -> tuple[ParseCaptureUseCase, FakeDrafts, FakeUsageCounters, FakeActionLog]:
    drafts = FakeDrafts()
    usage = usage or FakeUsageCounters()
    action_log = FakeActionLog()
    case = ParseCaptureUseCase(
        agent_model=model,
        tool_registry=registry(),
        drafts=drafts,
        usage_counters=usage,
        action_log=action_log,
        unit_of_work=FakeUnitOfWork(),
        accounts_reader=FakeAccountsReader(),
        categories_reader=FakeCategoriesReader(),
        plan_limits=PLAN_LIMITS,
        pricing=PRICING,
        model_name="fake-model",
    )
    return case, drafts, usage, action_log


def parse_input(text: str = "pagué 25 mil de almuerzo con nequi", **overrides: object):
    base: dict[str, object] = {
        "user_id": USER_ID,
        "currency": "COP",
        "tier": "free",
        "language": "es",
        "objective": "ahorrar",
        "today": TODAY,
        "text": text,
        "source": "voice",
    }
    base.update(overrides)
    return ParseCaptureInputDTO(**base)  # type: ignore[arg-type]


def stage_turn(**arguments: object):
    base: dict[str, object] = {
        "type": "expense",
        "amount": "25000",
        "description": "Almuerzo",
        "source_id": ACCOUNT_ID,
    }
    base.update(arguments)
    return turn(tool_calls=(ToolCall(id="c1", name="stage_movement_draft", arguments=base),))


@pytest.mark.asyncio
async def test_the_happy_path_is_one_forced_call() -> None:
    model = FakeAgentModel([stage_turn()])
    case, drafts, usage, log = use_case(model)

    output = await case.execute(parse_input())

    assert output.draft is not None
    assert output.clarification is None
    assert output.draft.amount == 25_000
    assert drafts.saved[0].captured_via == "voice"
    assert usage.consumed == [{"registrations": 1, "messages": 0}]
    assert output.usage.registrations.used == 1
    assert model.requests[0]["force_tool"] == "stage_movement_draft"
    assert log.entries[0].action == "parse_voice"
    assert log.entries[0].calls == 1


@pytest.mark.asyncio
async def test_typed_text_stamps_text_provenance() -> None:
    case, drafts, _, log = use_case(FakeAgentModel([stage_turn()]))

    await case.execute(parse_input(source="text"))

    assert drafts.saved[0].captured_via == "text"
    assert log.entries[0].action == "parse_text"


@pytest.mark.asyncio
async def test_an_ambiguous_capture_becomes_one_free_question() -> None:
    script = [
        stage_turn(source_id="acc-nope"),
        turn(
            tool_calls=(respond_call([{"type": "text", "text": "¿De qué cuenta salió la plata?"}]),)
        ),
    ]
    case, drafts, usage, _ = use_case(FakeAgentModel(script))

    output = await case.execute(parse_input("pagué 25"))

    assert output.draft is None
    assert output.clarification == "¿De qué cuenta salió la plata?"
    assert drafts.saved == []
    assert usage.consumed == []  # a question is not a captured movement
    assert output.usage.registrations.used == 0


@pytest.mark.asyncio
async def test_the_model_can_self_correct_on_the_free_call() -> None:
    script = [stage_turn(source_id="acc-nope"), stage_turn()]
    case, drafts, usage, _ = use_case(FakeAgentModel(script))

    output = await case.execute(parse_input())

    assert output.draft is not None
    assert len(drafts.saved) == 1
    assert usage.consumed == [{"registrations": 1, "messages": 0}]


@pytest.mark.asyncio
async def test_a_read_tool_detour_still_ends_in_the_forced_question() -> None:
    script = [
        stage_turn(source_id="acc-nope"),
        turn(tool_calls=(ToolCall(id="r1", name="get_accounts_overview", arguments={}),)),
        turn(tool_calls=(respond_call([{"type": "text", "text": "¿Nequi o Visa?"}]),)),
    ]
    model = FakeAgentModel(script)
    case, _, usage, log = use_case(model)

    output = await case.execute(parse_input())

    assert output.clarification == "¿Nequi o Visa?"
    assert usage.consumed == []
    assert model.requests[2]["force_tool"] == "respond_with_blocks"
    assert log.entries[0].calls == 3


@pytest.mark.asyncio
async def test_invalid_final_blocks_fall_back_to_the_canned_line() -> None:
    script = [
        stage_turn(source_id="acc-nope"),
        turn(
            tool_calls=(
                respond_call([{"type": "navigate", "label": "x", "route": "https://evil"}]),
            )
        ),
    ]
    case, _, _, _ = use_case(FakeAgentModel(script))

    output = await case.execute(parse_input())

    assert output.clarification is not None
    assert "No logré" in output.clarification


@pytest.mark.asyncio
async def test_the_gate_runs_before_any_model_call() -> None:
    model = FakeAgentModel([])
    case, _, _, _ = use_case(model, usage=FakeUsageCounters(registrations_used=60))

    with pytest.raises(RegistrationLimitReachedError):
        await case.execute(parse_input())

    assert model.requests == []


@pytest.mark.asyncio
async def test_the_capture_instruction_and_text_ride_the_user_message() -> None:
    model = FakeAgentModel([stage_turn()])
    case, _, _, _ = use_case(model)

    await case.execute(parse_input("gasté 12 lucas en café"))

    prompt = model.requests[0]["messages"][-1].text
    assert "[context]" in prompt
    assert "stage_movement_draft" in prompt  # the capture instruction
    assert "gasté 12 lucas en café" in prompt
    assert model.requests[0]["system"].startswith("Eres")
