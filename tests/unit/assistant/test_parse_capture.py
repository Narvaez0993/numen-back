"""The capture mini-loop: one forced call in the happy path, one honest
question when the text is ambiguous, and the registration gate before any
model call. Money rules mirror the chat's."""

import pytest

from src.modules.assistant.application.dto.parse import ParseCaptureInputDTO
from src.modules.assistant.application.ports.agent_model import FORCE_ANY_TOOL, ToolCall
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
    FakeDebtDrafts,
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
    debt_drafts = FakeDebtDrafts()
    usage = usage or FakeUsageCounters()
    action_log = FakeActionLog()
    case = ParseCaptureUseCase(
        agent_model=model,
        tool_registry=registry(),
        drafts=drafts,
        debt_drafts=debt_drafts,
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

    assert len(output.drafts) == 1
    assert output.clarification is None
    assert output.drafts[0].amount == 25_000
    assert drafts.saved[0].captured_via == "voice"
    assert usage.consumed == [{"registrations": 1, "messages": 0}]
    assert output.usage.registrations.used == 1
    # Forced to stage SOMETHING, not forced to stage a movement: which capture the
    # sentence is belongs to the model. Naming one tool here is what used to turn
    # "le presté 50 mil a Andrés" into an expense.
    assert model.requests[0]["force_tool"] == FORCE_ANY_TOOL
    assert log.entries[0].action == "parse_voice"
    assert log.entries[0].calls == 1


@pytest.mark.asyncio
async def test_one_breath_with_three_expenses_stages_three_drafts() -> None:
    """«10 mil en café, 5 mil en papitas, 8 mil en un mouse» is three movements,
    not one. The model stages them as parallel calls in a single turn — running
    only the first is how the other two used to disappear."""
    spoken = [("Café", "10000"), ("Papitas", "5000"), ("Mouse", "8000")]
    model = FakeAgentModel(
        [
            turn(
                tool_calls=tuple(
                    ToolCall(
                        id=f"c{index}",
                        name="stage_movement_draft",
                        arguments={
                            "type": "expense",
                            "amount": amount,
                            "description": description,
                            "source_id": ACCOUNT_ID,
                        },
                    )
                    for index, (description, amount) in enumerate(spoken)
                )
            )
        ]
    )
    case, drafts, usage, _ = use_case(model)

    output = await case.execute(parse_input("10 mil en café, 5 mil en papitas y 8 mil en un mouse"))

    assert [draft.description for draft in output.drafts] == ["Café", "Papitas", "Mouse"]
    assert [draft.amount for draft in output.drafts] == [10_000, 5_000, 8_000]
    assert len(drafts.saved) == 3
    # Three movements recorded is three registrations — the quota counts what
    # landed in the ledger, not how many times the user pressed the mic.
    assert usage.consumed == [{"registrations": 3, "messages": 0}]
    assert output.usage.registrations.used == 3


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

    assert output.drafts == []
    assert output.clarification == "¿De qué cuenta salió la plata?"
    assert drafts.saved == []
    assert usage.consumed == []  # a question is not a captured movement
    assert output.usage.registrations.used == 0


@pytest.mark.asyncio
async def test_the_model_can_self_correct_on_the_free_call() -> None:
    script = [stage_turn(source_id="acc-nope"), stage_turn()]
    case, drafts, usage, _ = use_case(FakeAgentModel(script))

    output = await case.execute(parse_input())

    assert len(output.drafts) == 1
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
