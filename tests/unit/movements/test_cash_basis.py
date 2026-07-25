"""The cash-basis table — the most important rule in the product.

Each case asserts the resulting positions *and*, for transfers, that the net
position is unchanged: moving money between your own sources must never make you
richer or poorer. See docs/02-reglas-de-negocio.md §2.
"""

import pytest

from src.modules.movements.application.services.movement_references import (
    MovementReferences,
)
from src.modules.movements.application.use_cases.create_movement import CreateMovementUseCase

from .fakes import (
    CURRENCY,
    TODAY,
    FakeCategoryLookup,
    FakeSourceLedger,
    FixedClock,
    ImmediateUnitOfWork,
    InMemoryIdempotencyStore,
    InMemoryMovementRepository,
    new_user_id,
)
from .helpers import create_input


def build(ledger: FakeSourceLedger) -> CreateMovementUseCase:
    return CreateMovementUseCase(
        movement_repository=InMemoryMovementRepository(),
        source_ledger=ledger,
        references=MovementReferences(source_ledger=ledger, category_lookup=FakeCategoryLookup()),
        idempotency_store=InMemoryIdempotencyStore(),
        unit_of_work=ImmediateUnitOfWork(),
        clock=FixedClock(),
    )


def net(ledger: FakeSourceLedger) -> int:
    """Assets minus liabilities, the same formula the accounts overview uses."""
    return sum(ledger.accounts.values()) - sum(ledger.cards.values())


@pytest.mark.asyncio
async def test_expense_from_an_account_lowers_its_balance() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    user_id = new_user_id()

    await build(ledger).execute(
        create_input(user_id, type="expense", amount=50_000, source_id="nequi")
    )

    assert ledger.accounts["nequi"] == 950_000


@pytest.mark.asyncio
async def test_expense_on_a_card_raises_the_debt_and_leaves_balances_alone() -> None:
    """A card charge is an expense today even though no cash left the account."""
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000}, cards={"visa": 200_000})
    user_id = new_user_id()

    await build(ledger).execute(
        create_input(
            user_id,
            type="expense",
            amount=300_000,
            source_type="credit_card",
            source_id="visa",
        )
    )

    assert ledger.cards["visa"] == 500_000
    assert ledger.accounts["nequi"] == 1_000_000
    # You are 300k poorer the moment you buy, not when you pay the card.
    assert net(ledger) == 500_000


@pytest.mark.asyncio
async def test_income_to_an_account_raises_its_balance() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    user_id = new_user_id()

    await build(ledger).execute(
        create_input(
            user_id,
            type="income",
            amount=3_000_000,
            source_id="nequi",
            category_id="salario",
        )
    )

    assert ledger.accounts["nequi"] == 4_000_000


@pytest.mark.asyncio
async def test_paying_a_card_lowers_debt_and_balance_and_keeps_the_net() -> None:
    """The acid test of cash-basis: a payment is a transfer, not an expense."""
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000}, cards={"visa": 800_000})
    user_id = new_user_id()
    before = net(ledger)

    await build(ledger).execute(
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

    assert ledger.accounts["nequi"] == 500_000
    assert ledger.cards["visa"] == 300_000
    assert net(ledger) == before


@pytest.mark.asyncio
async def test_transfer_between_accounts_keeps_the_net() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000, "banco": 200_000})
    user_id = new_user_id()
    before = net(ledger)

    await build(ledger).execute(
        create_input(
            user_id,
            type="transfer",
            amount=400_000,
            source_id="nequi",
            destination_type="account",
            destination_id="banco",
            category_id=None,
        )
    )

    assert ledger.accounts == {"nequi": 600_000, "banco": 600_000}
    assert net(ledger) == before


@pytest.mark.asyncio
async def test_cash_advance_raises_debt_and_balance_and_keeps_the_net() -> None:
    """Taking cash out of a card: the mirror image of paying it."""
    ledger = FakeSourceLedger(accounts={"efectivo": 0}, cards={"visa": 100_000})
    user_id = new_user_id()
    before = net(ledger)

    await build(ledger).execute(
        create_input(
            user_id,
            type="transfer",
            amount=200_000,
            source_type="credit_card",
            source_id="visa",
            destination_type="account",
            destination_id="efectivo",
            category_id=None,
        )
    )

    assert ledger.cards["visa"] == 300_000
    assert ledger.accounts["efectivo"] == 200_000
    assert net(ledger) == before


@pytest.mark.asyncio
async def test_an_expense_can_overdraw_an_account() -> None:
    """We record what happened; we do not refuse reality."""
    ledger = FakeSourceLedger(accounts={"nequi": 10_000})
    user_id = new_user_id()

    await build(ledger).execute(
        create_input(user_id, type="expense", amount=50_000, source_id="nequi")
    )

    assert ledger.accounts["nequi"] == -40_000


@pytest.mark.asyncio
async def test_a_card_charge_can_exceed_the_limit() -> None:
    ledger = FakeSourceLedger(cards={"visa": 4_900_000})
    user_id = new_user_id()

    await build(ledger).execute(
        create_input(
            user_id,
            type="expense",
            amount=200_000,
            source_type="credit_card",
            source_id="visa",
        )
    )

    assert ledger.cards["visa"] == 5_100_000


@pytest.mark.asyncio
async def test_the_whole_write_runs_inside_one_unit_of_work() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000}, cards={"visa": 800_000})
    unit_of_work = ImmediateUnitOfWork()
    use_case = CreateMovementUseCase(
        movement_repository=InMemoryMovementRepository(),
        source_ledger=ledger,
        references=MovementReferences(source_ledger=ledger, category_lookup=FakeCategoryLookup()),
        idempotency_store=InMemoryIdempotencyStore(),
        unit_of_work=unit_of_work,
        clock=FixedClock(),
    )

    await use_case.execute(
        create_input(
            new_user_id(),
            type="transfer",
            amount=100_000,
            source_id="nequi",
            destination_type="credit_card",
            destination_id="visa",
            category_id=None,
        )
    )

    assert unit_of_work.calls == 1


@pytest.mark.asyncio
async def test_the_movement_is_stored_with_a_positive_amount_and_its_currency() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    repository = InMemoryMovementRepository()
    use_case = CreateMovementUseCase(
        movement_repository=repository,
        source_ledger=ledger,
        references=MovementReferences(source_ledger=ledger, category_lookup=FakeCategoryLookup()),
        idempotency_store=InMemoryIdempotencyStore(),
        unit_of_work=ImmediateUnitOfWork(),
        clock=FixedClock(),
    )

    output = await use_case.execute(
        create_input(new_user_id(), type="expense", amount=50_000, source_id="nequi")
    )

    stored = repository.movements[0]
    assert output.amount == 50_000
    assert stored.amount == 50_000
    assert stored.currency == CURRENCY
    assert stored.occurred_on == TODAY
    assert stored.captured_via == "manual"
