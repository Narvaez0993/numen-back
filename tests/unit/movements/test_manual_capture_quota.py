"""HU-13 · a manual expense never touches the assisted-capture quota."""

import pytest

from src.modules.assistant.application.use_cases.get_usage import GetUsageUseCase, UsageInputDTO
from src.modules.movements.application.services.movement_references import (
    MovementReferences,
)
from src.modules.movements.application.use_cases.create_movement import CreateMovementUseCase
from tests.unit.assistant.fakes import PLAN_LIMITS, FakeUsageCounters

from .fakes import (
    FakeCategoryLookup,
    FakeSourceLedger,
    FixedClock,
    ImmediateUnitOfWork,
    InMemoryIdempotencyStore,
    InMemoryMovementRepository,
    new_user_id,
)
from .helpers import create_input


@pytest.mark.asyncio
async def test_hu13_a_manual_expense_is_saved_and_no_usage_counter_moves() -> None:
    """HU-13 · «El registro manual no consume cuota»: plan gratuito con los registros
    asistidos del mes agotados; el gasto a mano se guarda y ningún contador cambia.

    `CreateMovementUseCase` has no dependency on the counters, so the proof reads them
    through the assistant's own meter (`GetUsageUseCase` over its counters) before and
    after, and also asserts nothing was ever consumed.
    """
    user_id = new_user_id()
    exhausted = PLAN_LIMITS.registrations_free
    counters = FakeUsageCounters(registrations_used=exhausted, messages_used=3)
    meter = GetUsageUseCase(usage_counters=counters, plan_limits=PLAN_LIMITS)
    usage_input = UsageInputDTO(user_id=user_id, tier="free", today="2026-07-25")
    before = await meter.execute(usage_input)
    assert before.registrations.used == before.registrations.limit  # quota exhausted

    repository = InMemoryMovementRepository()
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    use_case = CreateMovementUseCase(
        movement_repository=repository,
        source_ledger=ledger,
        references=MovementReferences(source_ledger=ledger, category_lookup=FakeCategoryLookup()),
        idempotency_store=InMemoryIdempotencyStore(),
        unit_of_work=ImmediateUnitOfWork(),
        clock=FixedClock(),
    )

    created = await use_case.execute(create_input(user_id, captured_via="manual", amount=12_000))

    assert [m.id for m in repository.movements] == [created.id]
    assert ledger.accounts["nequi"] == 988_000
    after = await meter.execute(usage_input)
    assert after == before
    assert counters.consumed == []
