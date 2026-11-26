"""The global cap measured against real movements, not a canned spend reader.

`FakeSpendReader` answers with fixed numbers, so it cannot show that an income stays
out of the consumption or that the month boundary resets it. These tests wire the real
`MovementsSpendReader` over the in-memory movement repository.
"""

from datetime import timedelta
from uuid import UUID

import pytest

from src.modules.budgets.adapters.outbound.spend.movements_spend_reader import (
    MovementsSpendReader,
)
from src.modules.budgets.application.dto.budget_commands import GlobalCapInputDTO
from src.modules.budgets.application.use_cases.get_global_cap import GetGlobalCapUseCase
from src.modules.movements.application.use_cases.get_top_merchants import GetTopMerchantsUseCase
from src.modules.movements.application.use_cases.summarize_movements import (
    SummarizeMovementsUseCase,
)
from src.modules.movements.domain.entities.movement import Movement, SourceRef
from tests.unit.movements.fakes import FIXED_NOW, InMemoryMovementRepository

from .fakes import CURRENCY, FakeBudgetRepository, budget, new_user_id


def make_movement(
    user_id: UUID, *, type: str, amount: int, occurred_on: str, order: int = 0
) -> Movement:
    return Movement(
        id=f"mov-{type}-{amount}-{occurred_on}-{order}",
        user_id=user_id,
        type=type,  # type: ignore[arg-type]
        description="x",
        amount=amount,
        currency=CURRENCY,
        source=SourceRef(type="account", id="nequi"),
        destination=None,
        category_id="salario" if type == "income" else "mercado",
        occurred_on=occurred_on,
        captured_via="manual",
        created_at=FIXED_NOW + timedelta(minutes=order),
    )


def cap_reader(movements: InMemoryMovementRepository, budgets: FakeBudgetRepository):
    reader = MovementsSpendReader(
        summarize_movements=SummarizeMovementsUseCase(movement_repository=movements),
        get_top_merchants=GetTopMerchantsUseCase(movement_repository=movements),
    )
    return GetGlobalCapUseCase(budget_repository=budgets, spend_reader=reader)


@pytest.mark.asyncio
async def test_hu14_an_income_does_not_move_the_cap_consumption() -> None:
    """HU-14 · «El ingreso no cuenta como gasto»: con un tope definido, registrar un
    ingreso no cambia el consumo del tope."""
    user_id = new_user_id()
    budgets = FakeBudgetRepository([budget(user_id=user_id, target=2_500_000, since="2026-07")])
    movements = InMemoryMovementRepository(
        make_movement(user_id, type="expense", amount=1_000_000, occurred_on="2026-07-10")
    )
    use_case = cap_reader(movements, budgets)
    query = GlobalCapInputDTO(user_id=user_id, today="2026-07-20")

    before = await use_case.execute(query)

    await movements.save(
        make_movement(user_id, type="income", amount=3_000_000, occurred_on="2026-07-15", order=1)
    )
    after = await use_case.execute(query)

    assert before is not None
    assert after is not None
    assert before.spent == 1_000_000
    assert after.spent == before.spent
    assert after.remaining == before.remaining == 1_500_000


@pytest.mark.asyncio
async def test_hu28_the_cap_set_in_may_still_rules_in_june_and_consumption_restarts_at_zero() -> (
    None
):
    """HU-28 · «El tope sigue vigente el mes siguiente»: definido en mayo y sin
    modificar, rige igual en junio y el consumo se reinicia en cero."""
    user_id = new_user_id()
    budgets = FakeBudgetRepository([budget(user_id=user_id, target=2_500_000, since="2026-05")])
    movements = InMemoryMovementRepository(
        make_movement(user_id, type="expense", amount=1_000_000, occurred_on="2026-05-12")
    )
    use_case = cap_reader(movements, budgets)

    in_may = await use_case.execute(GlobalCapInputDTO(user_id=user_id, today="2026-05-20"))
    in_june = await use_case.execute(GlobalCapInputDTO(user_id=user_id, today="2026-06-01"))

    assert in_may is not None
    assert in_may.spent == 1_000_000
    assert in_may.target == 2_500_000
    assert in_june is not None
    assert in_june.target == 2_500_000  # the same ceiling, untouched
    assert in_june.spent == 0  # May's spending does not carry over
    assert in_june.remaining == 2_500_000
