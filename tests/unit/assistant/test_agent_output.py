"""The AgentOutput aggregate: play transitions, idempotent add, frozen unions,
and the period arithmetic every proactive job leans on."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.modules.assistant.adapters.outbound.persistence.mappers.agent_output_mapper import (
    _play_from,
    _play_to,
)
from src.modules.assistant.application.dto.plays import (
    PLAY_ADAPTER,
    params_of,
    play_dto_from_domain,
)
from src.modules.assistant.application.dto.slides import SLIDES_ADAPTER
from src.modules.assistant.application.ports.agent_output_repository import (
    AgentOutputAlreadyExistsError,
)
from src.modules.assistant.domain.entities.agent_output import (
    PLAY_APPLIED,
    PLAY_APPLYING,
    PLAY_FAILED,
    PLAY_PROPOSED,
)
from src.modules.assistant.domain.periods import (
    iso_week_bounds,
    month_bounds,
    previous_iso_week,
    previous_iso_week_label,
    previous_month,
    round_to_nice,
    round_to_nice_down,
)
from tests.unit.assistant.fakes import USER_ID, FakeAgentOutputRepository, agent_output, play

AT = datetime(2026, 8, 2, 10, 0, 0, tzinfo=UTC)


# --- play transitions (the fake mirrors Mongo's conditional write) ---


async def test_claim_then_complete_play() -> None:
    repo = FakeAgentOutputRepository()
    output = agent_output()
    await repo.add(output)

    claimed = await repo.transition_play(
        USER_ID, output.id, "play-1", from_status=PLAY_PROPOSED, to_status=PLAY_APPLYING
    )
    assert claimed is not None
    assert claimed.play("play-1").status == PLAY_APPLYING  # type: ignore[union-attr]

    done = await repo.transition_play(
        USER_ID,
        output.id,
        "play-1",
        from_status=PLAY_APPLYING,
        to_status=PLAY_APPLIED,
        result_id="budget-9",
        applied_at=AT,
    )
    assert done is not None
    applied = done.play("play-1")
    assert applied is not None
    assert applied.status == PLAY_APPLIED
    assert applied.result_id == "budget-9"
    assert applied.applied_at == AT


async def test_double_claim_loses_the_race() -> None:
    repo = FakeAgentOutputRepository()
    output = agent_output()
    await repo.add(output)

    first = await repo.transition_play(
        USER_ID, output.id, "play-1", from_status=PLAY_PROPOSED, to_status=PLAY_APPLYING
    )
    second = await repo.transition_play(
        USER_ID, output.id, "play-1", from_status=PLAY_PROPOSED, to_status=PLAY_APPLYING
    )
    assert first is not None
    assert second is None


async def test_fail_records_the_code() -> None:
    repo = FakeAgentOutputRepository()
    output = agent_output(plays=(play(status=PLAY_APPLYING),))
    await repo.add(output)

    failed = await repo.transition_play(
        USER_ID,
        output.id,
        "play-1",
        from_status=PLAY_APPLYING,
        to_status=PLAY_FAILED,
        failure_code="plan_limit",
    )
    assert failed is not None
    landed = failed.play("play-1")
    assert landed is not None
    assert landed.status == PLAY_FAILED
    assert landed.failure_code == "plan_limit"


async def test_transition_unknown_play_returns_none() -> None:
    repo = FakeAgentOutputRepository()
    output = agent_output()
    await repo.add(output)

    moved = await repo.transition_play(
        USER_ID, output.id, "ghost", from_status=PLAY_PROPOSED, to_status=PLAY_APPLYING
    )
    assert moved is None


async def test_duplicate_period_raises_already_exists() -> None:
    repo = FakeAgentOutputRepository()
    await repo.add(agent_output())

    with pytest.raises(AgentOutputAlreadyExistsError):
        await repo.add(agent_output())


async def test_mark_read_writes_once() -> None:
    repo = FakeAgentOutputRepository()
    output = agent_output()
    await repo.add(output)

    first = await repo.mark_read(USER_ID, output.id, AT)
    later = datetime(2026, 8, 9, 10, 0, 0, tzinfo=UTC)
    second = await repo.mark_read(USER_ID, output.id, later)
    assert first is not None
    assert first.read_at == AT
    assert second is not None
    assert second.read_at == AT


def test_treat_is_not_applyable() -> None:
    advice = play(action="treat", params={"amount": 50_000})
    assert not advice.applyable
    assert play().applyable


# --- unions: frozen snapshots, extra=forbid ---


def test_slides_union_round_trips() -> None:
    slides = [
        {"type": "cover", "id": "cover", "text": "Tu julio en 60 segundos"},
        {"type": "big_number", "id": "big_number", "amount": 1_250_000, "count": 42, "text": "x"},
        {
            "type": "category_bars",
            "id": "category_bars",
            "bars": [{"category_id": "comida", "name": "Comida", "amount": 400_000, "pct": 0.32}],
            "text": "x",
        },
        {
            "type": "fun_fact",
            "id": "fun_fact",
            "day": "2026-07-18",
            "amount": 180_000,
            "count": 6,
            "text": "x",
        },
        {
            "type": "pulse",
            "id": "pulse",
            "current": 1_250_000,
            "previous": 1_360_000,
            "delta_pct": -0.08,
            "text": "x",
        },
        {"type": "play", "id": "play", "play_id": "play-1", "text": "x"},
    ]
    parsed = SLIDES_ADAPTER.validate_python(slides)
    assert [s.type for s in parsed] == [s["id"] for s in slides]


def test_slides_union_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SLIDES_ADAPTER.validate_python(
            [{"type": "cover", "id": "cover", "text": "x", "surprise": True}]
        )


def test_play_dto_round_trips_params() -> None:
    domain = play(
        action="raise_category_cap",
        params={
            "budget_id": "b-1",
            "category_id": "comida",
            "category_name": "Comida",
            "current_target": 300_000,
            "target": 400_000,
        },
    )
    dto = play_dto_from_domain(domain)
    assert dto.action == "raise_category_cap"
    assert params_of(dto) == dict(domain.params)


def test_play_dto_rejects_missing_action_fields() -> None:
    with pytest.raises(ValidationError):
        PLAY_ADAPTER.validate_python(
            {"id": "p", "action": "contribute_goal", "text": "x", "status": "proposed"}
        )


def test_mapper_flattens_and_restores_params() -> None:
    original = play()
    raw = _play_to(original)
    assert raw["target"] == 400_000  # params live as siblings in Mongo
    assert _play_from(raw) == original


# --- periods: the only arithmetic the jobs trust ---


def test_previous_month_crosses_the_year() -> None:
    assert previous_month("2026-08-01") == "2026-07"
    assert previous_month("2026-01-15") == "2025-12"


def test_month_bounds() -> None:
    assert month_bounds("2026-07") == ("2026-07-01", "2026-07-31")
    assert month_bounds("2026-02") == ("2026-02-01", "2026-02-28")
    assert month_bounds("2026-12") == ("2026-12-01", "2026-12-31")


def test_previous_iso_week_on_a_monday() -> None:
    # Monday 2026-08-03 reviews the week that just ended: Jul 27 - Aug 2.
    assert previous_iso_week("2026-08-03") == "2026-W31"
    assert iso_week_bounds("2026-W31") == ("2026-07-27", "2026-08-02")
    assert previous_iso_week_label("2026-W31") == "2026-W30"


def test_round_to_nice() -> None:
    assert round_to_nice(287_450) == 290_000
    assert round_to_nice(1_000) == 1_000
    assert round_to_nice(0) == 0
    assert round_to_nice_down(56_780) == 56_000
    assert round_to_nice_down(999) == 990
