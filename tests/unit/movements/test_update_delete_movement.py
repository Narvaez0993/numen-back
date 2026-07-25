"""Editing and deleting must re-settle the money, not double-count it.

The bug this design exists to prevent: raising an expense from 50k to 80k leaving
the account 130k lower. Every case here asserts the resulting position.
"""

import pytest

from src.modules.movements.application.dto.movement_commands import (
    DeleteMovementInputDTO,
    UpdateMovementInputDTO,
)
from src.modules.movements.application.services.movement_references import (
    MovementReferences,
)
from src.modules.movements.application.use_cases.create_movement import CreateMovementUseCase
from src.modules.movements.application.use_cases.delete_movement import DeleteMovementUseCase
from src.modules.movements.application.use_cases.update_movement import UpdateMovementUseCase
from src.modules.movements.domain.errors import (
    InvalidMovementError,
    MovementCategoryNotFoundError,
    MovementNotFoundError,
    SourceNotFoundError,
)

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


def build_creator(
    ledger: FakeSourceLedger, repository: InMemoryMovementRepository
) -> CreateMovementUseCase:
    return CreateMovementUseCase(
        movement_repository=repository,
        source_ledger=ledger,
        references=MovementReferences(source_ledger=ledger, category_lookup=FakeCategoryLookup()),
        idempotency_store=InMemoryIdempotencyStore(),
        unit_of_work=ImmediateUnitOfWork(),
        clock=FixedClock(),
    )


def build_updater(
    ledger: FakeSourceLedger, repository: InMemoryMovementRepository
) -> UpdateMovementUseCase:
    return UpdateMovementUseCase(
        movement_repository=repository,
        source_ledger=ledger,
        references=MovementReferences(source_ledger=ledger, category_lookup=FakeCategoryLookup()),
        unit_of_work=ImmediateUnitOfWork(),
        clock=FixedClock(),
    )


def build_deleter(
    ledger: FakeSourceLedger, repository: InMemoryMovementRepository
) -> DeleteMovementUseCase:
    return DeleteMovementUseCase(
        movement_repository=repository,
        source_ledger=ledger,
        unit_of_work=ImmediateUnitOfWork(),
    )


def net(ledger: FakeSourceLedger) -> int:
    return sum(ledger.accounts.values()) - sum(ledger.cards.values())


# --- editing the amount ------------------------------------------------------


@pytest.mark.asyncio
async def test_raising_an_expense_settles_the_difference_only() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(user_id, amount=50_000, source_id="nequi")
    )

    await build_updater(ledger, repository).execute(
        UpdateMovementInputDTO(user_id=user_id, movement_id=created.id, amount=80_000)
    )

    # 1.000.000 - 80.000, not - 130.000.
    assert ledger.accounts["nequi"] == 920_000


@pytest.mark.asyncio
async def test_lowering_an_expense_gives_money_back() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(user_id, amount=80_000, source_id="nequi")
    )

    await build_updater(ledger, repository).execute(
        UpdateMovementInputDTO(user_id=user_id, movement_id=created.id, amount=20_000)
    )

    assert ledger.accounts["nequi"] == 980_000


@pytest.mark.asyncio
async def test_editing_a_card_charge_adjusts_the_debt() -> None:
    ledger = FakeSourceLedger(cards={"visa": 0})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(user_id, amount=300_000, source_type="credit_card", source_id="visa")
    )

    await build_updater(ledger, repository).execute(
        UpdateMovementInputDTO(user_id=user_id, movement_id=created.id, amount=250_000)
    )

    assert ledger.cards["visa"] == 250_000


# --- moving a movement between sources ---------------------------------------


@pytest.mark.asyncio
async def test_changing_the_source_moves_the_whole_delta() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000, "banco": 1_000_000})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(user_id, amount=50_000, source_id="nequi")
    )

    await build_updater(ledger, repository).execute(
        UpdateMovementInputDTO(
            user_id=user_id,
            movement_id=created.id,
            source_type="account",
            source_id="banco",
        )
    )

    # The account that never spent it gets it back; the new one pays.
    assert ledger.accounts == {"nequi": 1_000_000, "banco": 950_000}


@pytest.mark.asyncio
async def test_moving_an_expense_from_an_account_to_a_card() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000}, cards={"visa": 0})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(user_id, amount=90_000, source_id="nequi")
    )

    await build_updater(ledger, repository).execute(
        UpdateMovementInputDTO(
            user_id=user_id,
            movement_id=created.id,
            source_type="credit_card",
            source_id="visa",
        )
    )

    assert ledger.accounts["nequi"] == 1_000_000
    assert ledger.cards["visa"] == 90_000


@pytest.mark.asyncio
async def test_editing_a_card_payment_keeps_the_net_and_both_sides_right() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000}, cards={"visa": 800_000})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    before = net(ledger)
    created = await build_creator(ledger, repository).execute(
        create_input(
            user_id,
            type="transfer",
            amount=500_000,
            source_id="nequi",
            destination_type="credit_card",
            destination_id="visa",
            category_id=None,
        )
    )

    await build_updater(ledger, repository).execute(
        UpdateMovementInputDTO(user_id=user_id, movement_id=created.id, amount=300_000)
    )

    assert ledger.accounts["nequi"] == 700_000
    assert ledger.cards["visa"] == 500_000
    assert net(ledger) == before


# --- edits that do not move money --------------------------------------------


@pytest.mark.asyncio
async def test_editing_only_the_description_leaves_balances_untouched() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(user_id, amount=50_000, source_id="nequi")
    )
    ledger.applied = 0

    output = await build_updater(ledger, repository).execute(
        UpdateMovementInputDTO(
            user_id=user_id, movement_id=created.id, description="Mercado del sábado"
        )
    )

    assert output.description == "Mercado del sábado"
    assert ledger.accounts["nequi"] == 950_000
    # No revert+apply pair: the money did not move, so no write pretended it did.
    assert ledger.applied == 0


@pytest.mark.asyncio
async def test_editing_the_category_leaves_balances_untouched() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(user_id, amount=50_000, source_id="nequi", category_id="cafe")
    )
    ledger.applied = 0

    output = await build_updater(ledger, repository).execute(
        UpdateMovementInputDTO(user_id=user_id, movement_id=created.id, category_id="mercado")
    )

    assert output.category_id == "mercado"
    assert ledger.applied == 0


@pytest.mark.asyncio
async def test_editing_the_date_leaves_balances_untouched() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(user_id, amount=50_000, source_id="nequi")
    )
    ledger.applied = 0

    output = await build_updater(ledger, repository).execute(
        UpdateMovementInputDTO(user_id=user_id, movement_id=created.id, occurred_on="2026-07-01")
    )

    assert output.occurred_on == "2026-07-01"
    assert ledger.accounts["nequi"] == 950_000
    assert ledger.applied == 0


# --- validation on the resulting state ---------------------------------------


@pytest.mark.asyncio
async def test_cannot_move_a_movement_to_a_source_that_does_not_exist() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(user_id, amount=50_000, source_id="nequi")
    )

    with pytest.raises(SourceNotFoundError):
        await build_updater(ledger, repository).execute(
            UpdateMovementInputDTO(
                user_id=user_id,
                movement_id=created.id,
                source_type="account",
                source_id="fantasma",
            )
        )
    assert ledger.accounts["nequi"] == 950_000


@pytest.mark.asyncio
async def test_cannot_file_an_expense_under_an_income_category() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(user_id, amount=50_000, source_id="nequi")
    )

    with pytest.raises(MovementCategoryNotFoundError):
        await build_updater(ledger, repository).execute(
            UpdateMovementInputDTO(user_id=user_id, movement_id=created.id, category_id="salario")
        )


@pytest.mark.asyncio
async def test_cannot_give_a_category_to_a_transfer() -> None:
    """Coherence is checked on the merged state, not on the patch alone."""
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000}, cards={"visa": 0})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(
            user_id,
            type="transfer",
            amount=100_000,
            source_id="nequi",
            destination_type="credit_card",
            destination_id="visa",
            category_id=None,
        )
    )

    with pytest.raises(InvalidMovementError):
        await build_updater(ledger, repository).execute(
            UpdateMovementInputDTO(user_id=user_id, movement_id=created.id, category_id="mercado")
        )


@pytest.mark.asyncio
async def test_rejects_a_future_date() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(user_id, amount=50_000, source_id="nequi")
    )

    with pytest.raises(InvalidMovementError):
        await build_updater(ledger, repository).execute(
            UpdateMovementInputDTO(
                user_id=user_id, movement_id=created.id, occurred_on="2126-01-01"
            )
        )


@pytest.mark.asyncio
async def test_accepts_tomorrow_as_the_timezone_grace() -> None:
    """A client a day ahead of the server's UTC date is registering a real today."""
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(user_id, amount=50_000, source_id="nequi")
    )

    output = await build_updater(ledger, repository).execute(
        UpdateMovementInputDTO(user_id=user_id, movement_id=created.id, occurred_on="2026-07-26")
    )

    assert output.occurred_on == "2026-07-26"


@pytest.mark.asyncio
async def test_cannot_edit_another_users_movement() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    repository = InMemoryMovementRepository()
    created = await build_creator(ledger, repository).execute(
        create_input(new_user_id(), amount=50_000, source_id="nequi")
    )

    with pytest.raises(MovementNotFoundError):
        await build_updater(ledger, repository).execute(
            UpdateMovementInputDTO(user_id=new_user_id(), movement_id=created.id, amount=1_000)
        )


# --- deleting ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_deleting_an_expense_gives_the_money_back() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(user_id, amount=50_000, source_id="nequi")
    )

    await build_deleter(ledger, repository).execute(
        DeleteMovementInputDTO(user_id=user_id, movement_id=created.id)
    )

    assert ledger.accounts["nequi"] == 1_000_000
    assert repository.movements == []


@pytest.mark.asyncio
async def test_deleting_a_card_payment_restores_balance_and_debt() -> None:
    """This is what makes "undo" honest on a transfer."""
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000}, cards={"visa": 800_000})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(
            user_id,
            type="transfer",
            amount=500_000,
            source_id="nequi",
            destination_type="credit_card",
            destination_id="visa",
            category_id=None,
        )
    )

    await build_deleter(ledger, repository).execute(
        DeleteMovementInputDTO(user_id=user_id, movement_id=created.id)
    )

    assert ledger.accounts["nequi"] == 1_000_000
    assert ledger.cards["visa"] == 800_000


@pytest.mark.asyncio
async def test_deleting_a_card_charge_lowers_the_debt_back() -> None:
    ledger = FakeSourceLedger(cards={"visa": 100_000})
    repository = InMemoryMovementRepository()
    user_id = new_user_id()
    created = await build_creator(ledger, repository).execute(
        create_input(user_id, amount=300_000, source_type="credit_card", source_id="visa")
    )

    await build_deleter(ledger, repository).execute(
        DeleteMovementInputDTO(user_id=user_id, movement_id=created.id)
    )

    assert ledger.cards["visa"] == 100_000


@pytest.mark.asyncio
async def test_cannot_delete_another_users_movement() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    repository = InMemoryMovementRepository()
    created = await build_creator(ledger, repository).execute(
        create_input(new_user_id(), amount=50_000, source_id="nequi")
    )

    with pytest.raises(MovementNotFoundError):
        await build_deleter(ledger, repository).execute(
            DeleteMovementInputDTO(user_id=new_user_id(), movement_id=created.id)
        )
    assert len(repository.movements) == 1
    assert ledger.accounts["nequi"] == 950_000
