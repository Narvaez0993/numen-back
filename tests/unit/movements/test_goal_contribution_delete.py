"""HU-24 · deleting a contribution to a goal gives the money back to the account."""

import pytest

from src.modules.movements.application.dto.goal_funds import GoalFundsInputDTO
from src.modules.movements.application.dto.movement_commands import DeleteMovementInputDTO
from src.modules.movements.application.ports.source_ledger import SourceSnapshot
from src.modules.movements.application.services.movement_references import (
    MovementReferences,
)
from src.modules.movements.application.use_cases.create_movement import CreateMovementUseCase
from src.modules.movements.application.use_cases.delete_movement import DeleteMovementUseCase
from src.modules.movements.application.use_cases.get_goal_funds import GetGoalFundsUseCase
from src.modules.movements.domain.entities.movement import SourceRef

from .fakes import (
    CURRENCY,
    FakeCategoryLookup,
    FakeSourceLedger,
    FixedClock,
    ImmediateUnitOfWork,
    InMemoryIdempotencyStore,
    InMemoryMovementRepository,
    new_user_id,
)
from .helpers import create_input


class LedgerWithAPocket(FakeSourceLedger):
    """Like the routing ledger: the pocket resolves but has no balance to move."""

    async def find(self, user_id, ref: SourceRef) -> SourceSnapshot | None:  # type: ignore[no-untyped-def]
        if ref.type == "goal":
            return SourceSnapshot(ref=ref, type="goal", currency=CURRENCY)
        return await super().find(user_id, ref)

    async def apply_delta(self, user_id, ref: SourceRef, delta: int) -> None:  # type: ignore[no-untyped-def]
        if ref.type == "goal":
            return
        await super().apply_delta(user_id, ref, delta)


@pytest.mark.asyncio
async def test_hu24_deleting_a_contribution_returns_the_money_and_lowers_the_savings() -> None:
    """HU-24 · «Eliminación de un aporte a una meta»: aporte de 100.000 a «Viaje»;
    al eliminarlo, lo ahorrado baja 100.000 y la cuenta de origen sube 100.000."""
    user_id = new_user_id()
    ledger = LedgerWithAPocket(accounts={"nequi": 1_000_000})
    repository = InMemoryMovementRepository()
    creator = CreateMovementUseCase(
        movement_repository=repository,
        source_ledger=ledger,
        references=MovementReferences(source_ledger=ledger, category_lookup=FakeCategoryLookup()),
        idempotency_store=InMemoryIdempotencyStore(),
        unit_of_work=ImmediateUnitOfWork(),
        clock=FixedClock(),
    )
    deleter = DeleteMovementUseCase(
        movement_repository=repository, source_ledger=ledger, unit_of_work=ImmediateUnitOfWork()
    )
    funds = GetGoalFundsUseCase(movement_repository=repository)

    contribution = await creator.execute(
        create_input(
            user_id,
            type="transfer",
            amount=100_000,
            source_id="nequi",
            destination_type="goal",
            destination_id="viaje",
            category_id=None,
        )
    )
    assert ledger.accounts["nequi"] == 900_000
    saved_before = (await funds.execute(GoalFundsInputDTO(user_id=user_id))).funds[0].saved
    assert saved_before == 100_000

    await deleter.execute(DeleteMovementInputDTO(user_id=user_id, movement_id=contribution.id))

    assert ledger.accounts["nequi"] == 1_000_000
    saved_after = sum(
        row.saved for row in (await funds.execute(GoalFundsInputDTO(user_id=user_id))).funds
    )
    assert saved_after == saved_before - 100_000 == 0
