"""Aplicar una jugada: claim atómico, ejecución por action, fallo como estado."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest

from src.modules.assistant.application.use_cases.apply_play import (
    ApplyPlayInputDTO,
    ApplyPlayUseCase,
)
from src.modules.assistant.domain.entities.agent_output import (
    PLAY_APPLIED,
    PLAY_FAILED,
    PLAY_PROPOSED,
)
from src.modules.assistant.domain.errors import (
    AccountRequiredError,
    AgentOutputNotFoundError,
    PlayExecutionError,
    PlayNotApplyableError,
    PlayNotFoundError,
)

from .fakes import USER_ID, FakeAgentOutputRepository, agent_output, play

NOW = datetime(2026, 8, 2, 10, 0, 0, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


class FakeBudgetWriter:
    def __init__(self, fail_with: str | None = None) -> None:
        self.fail_with = fail_with
        self.created: list[dict[str, Any]] = []
        self.raised: list[dict[str, Any]] = []

    async def create_cap(
        self,
        user_id: UUID,
        *,
        tier: str,
        today: str,
        scope: str,
        category_id: str | None,
        target: int,
    ) -> str:
        if self.fail_with:
            raise PlayExecutionError(self.fail_with)
        self.created.append({"scope": scope, "category_id": category_id, "target": target})
        return "budget-9"

    async def raise_cap(self, user_id: UUID, *, today: str, budget_id: str, target: int) -> str:
        if self.fail_with:
            raise PlayExecutionError(self.fail_with)
        self.raised.append({"budget_id": budget_id, "target": target})
        return budget_id


class FakeGoalContributor:
    def __init__(self) -> None:
        self.contributions: list[dict[str, Any]] = []

    async def contribute(
        self,
        user_id: UUID,
        *,
        currency: str,
        today: str,
        goal_id: str,
        account_id: str,
        amount: int,
    ) -> None:
        self.contributions.append({"goal_id": goal_id, "account_id": account_id, "amount": amount})


def build(
    outputs: FakeAgentOutputRepository,
    *,
    writer: FakeBudgetWriter | None = None,
    contributor: FakeGoalContributor | None = None,
) -> ApplyPlayUseCase:
    return ApplyPlayUseCase(
        outputs=outputs,
        budget_writer=writer or FakeBudgetWriter(),
        goal_contributor=contributor or FakeGoalContributor(),
        clock=FixedClock(),
    )


def apply_input(output_id: str, play_id: str = "play-1", account_id: str | None = None):
    return ApplyPlayInputDTO(
        user_id=USER_ID,
        tier="free",
        currency="COP",
        today="2026-08-02",
        output_id=output_id,
        play_id=play_id,
        account_id=account_id,
    )


@pytest.mark.asyncio
async def test_set_category_cap_applies_and_records_the_result() -> None:
    outputs = FakeAgentOutputRepository()
    corte = agent_output()
    await outputs.add(corte)
    writer = FakeBudgetWriter()

    result = await build(outputs, writer=writer).execute(apply_input(corte.id))

    applied = next(p for p in result.plays if p.id == "play-1")
    assert applied.status == PLAY_APPLIED
    assert applied.result_id == "budget-9"
    assert writer.created == [{"scope": "category", "category_id": "comida", "target": 400_000}]
    stored = outputs.outputs[corte.id].play("play-1")
    assert stored is not None
    assert stored.applied_at == NOW


@pytest.mark.asyncio
async def test_executor_failure_lands_as_failed_state_not_http() -> None:
    outputs = FakeAgentOutputRepository()
    corte = agent_output()
    await outputs.add(corte)

    result = await build(outputs, writer=FakeBudgetWriter(fail_with="plan_limit")).execute(
        apply_input(corte.id)
    )

    failed = next(p for p in result.plays if p.id == "play-1")
    assert failed.status == PLAY_FAILED
    assert failed.failure_code == "plan_limit"


@pytest.mark.asyncio
async def test_double_tap_returns_the_current_state_without_reexecuting() -> None:
    outputs = FakeAgentOutputRepository()
    corte = agent_output()
    await outputs.add(corte)
    writer = FakeBudgetWriter()
    use_case = build(outputs, writer=writer)

    first = await use_case.execute(apply_input(corte.id))
    second = await use_case.execute(apply_input(corte.id))

    assert first.plays[0].status == PLAY_APPLIED
    assert second.plays[0].status == PLAY_APPLIED
    assert len(writer.created) == 1  # the second tap executed nothing


@pytest.mark.asyncio
async def test_treat_is_never_a_button() -> None:
    outputs = FakeAgentOutputRepository()
    corte = agent_output(plays=(play(action="treat", params={"amount": 50_000}),))
    await outputs.add(corte)

    with pytest.raises(PlayNotApplyableError):
        await build(outputs).execute(apply_input(corte.id))
    stored = outputs.outputs[corte.id].play("play-1")
    assert stored is not None
    assert stored.status == PLAY_PROPOSED  # not even claimed


@pytest.mark.asyncio
async def test_contribute_requires_an_account_and_moves_real_money() -> None:
    outputs = FakeAgentOutputRepository()
    corte = agent_output(
        plays=(
            play(
                action="contribute_goal",
                params={"goal_id": "g-1", "goal_name": "Viaje", "amount": 120_000},
            ),
        )
    )
    await outputs.add(corte)
    contributor = FakeGoalContributor()
    use_case = build(outputs, contributor=contributor)

    with pytest.raises(AccountRequiredError):
        await use_case.execute(apply_input(corte.id))

    result = await use_case.execute(apply_input(corte.id, account_id="acc-nequi"))
    applied = result.plays[0]
    assert applied.status == PLAY_APPLIED
    assert applied.result_id is None  # the transfer IS the record
    assert contributor.contributions == [
        {"goal_id": "g-1", "account_id": "acc-nequi", "amount": 120_000}
    ]


@pytest.mark.asyncio
async def test_missing_output_and_play_are_404s() -> None:
    outputs = FakeAgentOutputRepository()
    corte = agent_output()
    await outputs.add(corte)
    use_case = build(outputs)

    with pytest.raises(AgentOutputNotFoundError):
        await use_case.execute(apply_input("ghost"))
    with pytest.raises(PlayNotFoundError):
        await use_case.execute(apply_input(corte.id, play_id="ghost"))
