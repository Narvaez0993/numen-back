import pytest

from src.modules.movements.application.use_cases.create_movement import CreateMovementUseCase
from src.modules.movements.domain.errors import (
    InvalidMovementError,
    MovementCategoryNotFoundError,
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


def build(
    *,
    ledger: FakeSourceLedger | None = None,
    repository: InMemoryMovementRepository | None = None,
    store: InMemoryIdempotencyStore | None = None,
) -> CreateMovementUseCase:
    return CreateMovementUseCase(
        movement_repository=repository or InMemoryMovementRepository(),
        source_ledger=ledger or FakeSourceLedger(accounts={"nequi": 1_000_000}, cards={"visa": 0}),
        category_lookup=FakeCategoryLookup(),
        idempotency_store=store or InMemoryIdempotencyStore(),
        unit_of_work=ImmediateUnitOfWork(),
        clock=FixedClock(),
    )


# --- coherence table ---------------------------------------------------------


@pytest.mark.asyncio
async def test_an_expense_cannot_carry_a_destination() -> None:
    with pytest.raises(InvalidMovementError):
        await build().execute(
            create_input(new_user_id(), destination_type="account", destination_id="banco")
        )


@pytest.mark.asyncio
async def test_a_transfer_needs_a_destination() -> None:
    with pytest.raises(InvalidMovementError):
        await build().execute(create_input(new_user_id(), type="transfer", category_id=None))


@pytest.mark.asyncio
async def test_a_transfer_cannot_target_its_own_source() -> None:
    with pytest.raises(InvalidMovementError):
        await build().execute(
            create_input(
                new_user_id(),
                type="transfer",
                category_id=None,
                destination_type="account",
                destination_id="nequi",
            )
        )


@pytest.mark.asyncio
async def test_a_transfer_cannot_carry_a_category() -> None:
    with pytest.raises(InvalidMovementError):
        await build().execute(
            create_input(
                new_user_id(),
                type="transfer",
                category_id="mercado",
                destination_type="credit_card",
                destination_id="visa",
            )
        )


@pytest.mark.asyncio
async def test_income_cannot_arrive_on_a_card() -> None:
    """v1 keeps refunds out; adjusting the debt by hand is the honest exit."""
    with pytest.raises(InvalidMovementError):
        await build().execute(
            create_input(
                new_user_id(),
                type="income",
                source_type="credit_card",
                source_id="visa",
                category_id="salario",
            )
        )


@pytest.mark.asyncio
async def test_a_destination_needs_both_parts() -> None:
    with pytest.raises(InvalidMovementError):
        await build().execute(
            create_input(new_user_id(), type="transfer", category_id=None, destination_id="banco")
        )


# --- field validation --------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("amount", [0, -1])
async def test_rejects_a_non_positive_amount(amount: int) -> None:
    with pytest.raises(InvalidMovementError):
        await build().execute(create_input(new_user_id(), amount=amount))


@pytest.mark.asyncio
async def test_rejects_a_blank_description() -> None:
    with pytest.raises(InvalidMovementError):
        await build().execute(create_input(new_user_id(), description="   "))


@pytest.mark.asyncio
@pytest.mark.parametrize("occurred_on", ["ayer", "2026-13-01", "2026-02-30", "25/07/2026"])
async def test_rejects_a_date_that_is_not_a_real_iso_day(occurred_on: str) -> None:
    with pytest.raises(InvalidMovementError):
        await build().execute(create_input(new_user_id(), occurred_on=occurred_on))


@pytest.mark.asyncio
async def test_rejects_an_unknown_type() -> None:
    with pytest.raises(InvalidMovementError):
        await build().execute(create_input(new_user_id(), type="refund"))


# --- references --------------------------------------------------------------


@pytest.mark.asyncio
async def test_rejects_a_source_that_does_not_exist() -> None:
    with pytest.raises(SourceNotFoundError):
        await build().execute(create_input(new_user_id(), source_id="fantasma"))


@pytest.mark.asyncio
async def test_rejects_a_destination_that_does_not_exist() -> None:
    with pytest.raises(SourceNotFoundError):
        await build().execute(
            create_input(
                new_user_id(),
                type="transfer",
                category_id=None,
                destination_type="account",
                destination_id="fantasma",
            )
        )


@pytest.mark.asyncio
async def test_rejects_a_source_in_another_currency() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 0})
    ledger.currency = "USD"

    with pytest.raises(InvalidMovementError):
        await build(ledger=ledger).execute(create_input(new_user_id()))


@pytest.mark.asyncio
async def test_rejects_an_unknown_category() -> None:
    with pytest.raises(MovementCategoryNotFoundError):
        await build().execute(create_input(new_user_id(), category_id="inventada"))


@pytest.mark.asyncio
async def test_rejects_an_expense_filed_under_an_income_category() -> None:
    """Flow is part of the reference: a salary is not a way to spend."""
    with pytest.raises(MovementCategoryNotFoundError):
        await build().execute(create_input(new_user_id(), category_id="salario"))


@pytest.mark.asyncio
async def test_a_category_is_optional() -> None:
    output = await build().execute(create_input(new_user_id(), category_id=None))

    assert output.category_id is None


# --- idempotency -------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_same_key_returns_the_original_movement() -> None:
    ledger = FakeSourceLedger(accounts={"nequi": 1_000_000})
    repository = InMemoryMovementRepository()
    store = InMemoryIdempotencyStore()
    use_case = build(ledger=ledger, repository=repository, store=store)
    user_id = new_user_id()

    first = await use_case.execute(create_input(user_id, idempotency_key="abc"))
    second = await use_case.execute(create_input(user_id, idempotency_key="abc"))

    assert first.id == second.id
    assert len(repository.movements) == 1
    # The money moved once, not twice — the whole point of the guard.
    assert ledger.accounts["nequi"] == 988_000


@pytest.mark.asyncio
async def test_a_different_key_creates_a_second_movement() -> None:
    repository = InMemoryMovementRepository()
    use_case = build(repository=repository)
    user_id = new_user_id()

    await use_case.execute(create_input(user_id, idempotency_key="abc"))
    await use_case.execute(create_input(user_id, idempotency_key="def"))

    assert len(repository.movements) == 2


@pytest.mark.asyncio
async def test_keys_are_scoped_per_user() -> None:
    repository = InMemoryMovementRepository()
    use_case = build(repository=repository)

    await use_case.execute(create_input(new_user_id(), idempotency_key="abc"))
    await use_case.execute(create_input(new_user_id(), idempotency_key="abc"))

    assert len(repository.movements) == 2


@pytest.mark.asyncio
async def test_without_a_key_nothing_is_deduplicated() -> None:
    repository = InMemoryMovementRepository()
    use_case = build(repository=repository)
    user_id = new_user_id()

    await use_case.execute(create_input(user_id))
    await use_case.execute(create_input(user_id))

    assert len(repository.movements) == 2
