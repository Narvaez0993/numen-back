"""The stage executor is the gate between what the model says and a valid draft."""

import json

import pytest

from src.modules.assistant.application.ports.agent_model import ToolCall
from src.modules.assistant.application.services.tool_registry import ToolContext

from .fakes import (
    ACCOUNT_ID,
    CARD_ID,
    CATEGORY_ID,
    CURRENCY,
    TODAY,
    USER_ID,
    FakeSoleSourceReader,
    registry,
)


def ctx(
    *, registrations_used: int = 0, registrations_limit: int = 60, staged_count: int = 0
) -> ToolContext:
    return ToolContext(
        user_id=USER_ID,
        currency=CURRENCY,
        today=TODAY,
        registrations_used=registrations_used,
        registrations_limit=registrations_limit,
        staged_count=staged_count,
    )


def stage_call(**arguments: object) -> ToolCall:
    base: dict[str, object] = {
        "type": "expense",
        "amount": "25000",
        "description": "Almuerzo",
        "source_id": ACCOUNT_ID,
    }
    base.update(arguments)
    return ToolCall(id="call-1", name="stage_movement_draft", arguments=base)


@pytest.mark.asyncio
async def test_staging_normalizes_and_returns_the_draft_id() -> None:
    outcome = await registry().execute(stage_call(category_id=CATEGORY_ID), ctx())
    assert not outcome.is_error
    assert outcome.draft is not None
    payload = json.loads(outcome.content)
    assert payload["draft_id"] == outcome.draft.id
    assert payload["amount_minor_units"] == 25_000
    assert outcome.draft.source_type == "account"
    assert not outcome.is_read


@pytest.mark.asyncio
async def test_the_source_type_is_resolved_never_trusted() -> None:
    outcome = await registry().execute(stage_call(source_id=CARD_ID), ctx())
    assert outcome.draft is not None
    assert outcome.draft.source_type == "credit_card"


@pytest.mark.asyncio
async def test_an_unknown_source_is_a_tool_error() -> None:
    outcome = await registry().execute(stage_call(source_id="acc-nope"), ctx())
    assert outcome.is_error
    assert "unknown source_id" in outcome.content


@pytest.mark.asyncio
async def test_a_capture_without_a_source_stages_without_one() -> None:
    """The user said "un café de 5000" and never said where from. Picking the
    likeliest account for them is the behaviour this test exists to prevent."""
    call = stage_call()
    del call.arguments["source_id"]

    outcome = await registry().execute(call, ctx())

    assert not outcome.is_error
    assert outcome.draft is not None
    assert outcome.draft.source_id is None
    assert outcome.draft.source_type is None


@pytest.mark.asyncio
async def test_the_only_source_a_user_owns_is_filled_in() -> None:
    """With one account and no cards there is nothing to choose — asking would
    be ceremony, not honesty."""
    call = stage_call()
    del call.arguments["source_id"]

    outcome = await registry(FakeSoleSourceReader()).execute(call, ctx())

    assert outcome.draft is not None
    assert outcome.draft.source_id == ACCOUNT_ID
    assert outcome.draft.source_type == "account"


@pytest.mark.asyncio
async def test_a_category_of_the_wrong_flow_is_rejected() -> None:
    outcome = await registry().execute(
        stage_call(type="income", description="Sueldo", category_id=CATEGORY_ID), ctx()
    )
    assert outcome.is_error
    assert "not a income category" in outcome.content


@pytest.mark.asyncio
async def test_the_future_is_not_a_valid_movement_date() -> None:
    outcome = await registry().execute(stage_call(occurred_on="2026-07-29"), ctx())
    assert outcome.is_error
    assert "future" in outcome.content


@pytest.mark.asyncio
async def test_a_transfer_needs_a_distinct_destination_and_drops_the_category() -> None:
    outcome = await registry().execute(
        stage_call(
            type="transfer", destination_id=CARD_ID, category_id=CATEGORY_ID, description=""
        ),
        ctx(),
    )
    assert outcome.draft is not None
    assert outcome.draft.destination_type == "credit_card"
    assert outcome.draft.category_id is None

    same_ends = await registry().execute(
        stage_call(type="transfer", destination_id=ACCOUNT_ID), ctx()
    )
    assert same_ends.is_error


@pytest.mark.asyncio
async def test_exhausted_registrations_answer_with_a_hint_not_a_draft() -> None:
    outcome = await registry().execute(stage_call(), ctx(registrations_used=59, staged_count=1))
    assert outcome.is_error
    assert outcome.draft is None
    assert "quota" in outcome.content


@pytest.mark.asyncio
async def test_an_unknown_tool_is_an_error_result_not_a_crash() -> None:
    outcome = await registry().execute(ToolCall(id="x", name="does_not_exist", arguments={}), ctx())
    assert outcome.is_error


@pytest.mark.asyncio
async def test_read_tools_mark_the_outcome_as_read() -> None:
    outcome = await registry().execute(
        ToolCall(id="x", name="get_month_summary", arguments={}), ctx()
    )
    assert outcome.is_read
    payload = json.loads(outcome.content)
    assert payload["date_from"] == "2026-07-01"
    assert payload["date_to"] == "2026-07-31"


def test_the_toolset_is_fixed_and_ends_with_the_terminal_tool() -> None:
    specs = registry().specs()
    names = [spec.name for spec in specs]
    assert len(names) == 14
    assert names[-1] == "respond_with_blocks"
    assert "stage_movement_draft" in names
    assert "stage_debt_draft" in names
    assert "stage_debt_payment_draft" in names
