"""What a period added up to — the numbers Home, budgets and the agent all read."""

from datetime import timedelta
from uuid import UUID

import pytest

from src.modules.movements.application.dto.movement_summary import (
    SummarizeMovementsInputDTO,
)
from src.modules.movements.application.use_cases.summarize_movements import (
    SummarizeMovementsUseCase,
)
from src.modules.movements.domain.entities.movement import Movement, SourceRef
from src.modules.movements.domain.errors import InvalidMovementError

from .fakes import CURRENCY, FIXED_NOW, InMemoryMovementRepository, new_user_id

JULY = ("2026-07-01", "2026-07-31")


def movement(
    user_id: UUID,
    *,
    type: str = "expense",
    amount: int = 10_000,
    category_id: str | None = "cafe",
    occurred_on: str = "2026-07-10",
    order: int = 0,
) -> Movement:
    return Movement(
        id=f"mov-{type}-{amount}-{occurred_on}-{order}",
        user_id=user_id,
        type=type,  # type: ignore[arg-type]
        description="X",
        amount=amount,
        currency=CURRENCY,
        source=SourceRef(type="account", id="nequi"),
        destination=(SourceRef(type="credit_card", id="visa") if type == "transfer" else None),
        category_id=None if type == "transfer" else category_id,
        occurred_on=occurred_on,
        captured_via="manual",
        created_at=FIXED_NOW + timedelta(minutes=order),
    )


def build(repository: InMemoryMovementRepository) -> SummarizeMovementsUseCase:
    return SummarizeMovementsUseCase(movement_repository=repository)


async def summarize(
    repository: InMemoryMovementRepository, user_id: UUID, period: tuple[str, str] = JULY
):
    return await build(repository).execute(
        SummarizeMovementsInputDTO(user_id=user_id, date_from=period[0], date_to=period[1])
    )


@pytest.mark.asyncio
async def test_an_empty_period_is_all_zeros() -> None:
    output = await summarize(InMemoryMovementRepository(), new_user_id())

    assert (output.expense_total, output.income_total, output.count) == (0, 0, 0)
    assert output.by_category == []


@pytest.mark.asyncio
async def test_totals_split_expenses_from_income() -> None:
    user_id = new_user_id()
    repository = InMemoryMovementRepository(
        movement(user_id, amount=50_000, order=1),
        movement(user_id, amount=30_000, order=2),
        movement(user_id, type="income", amount=3_000_000, category_id="salario"),
    )

    output = await summarize(repository, user_id)

    assert output.expense_total == 80_000
    assert output.income_total == 3_000_000
    assert output.count == 3


@pytest.mark.asyncio
async def test_transfers_count_as_movements_but_are_neither_total() -> None:
    """Paying a card is not spending and not earning — the cash-basis rule."""
    user_id = new_user_id()
    repository = InMemoryMovementRepository(
        movement(user_id, amount=50_000),
        movement(user_id, type="transfer", amount=500_000, order=1),
    )

    output = await summarize(repository, user_id)

    assert output.expense_total == 50_000
    assert output.income_total == 0
    assert output.count == 2
    # And a transfer never shows up as spend in a category.
    assert [c.category_id for c in output.by_category] == ["cafe"]


@pytest.mark.asyncio
async def test_groups_spend_by_category_biggest_first() -> None:
    user_id = new_user_id()
    repository = InMemoryMovementRepository(
        movement(user_id, amount=10_000, category_id="cafe", order=1),
        movement(user_id, amount=5_000, category_id="cafe", order=2),
        movement(user_id, amount=400_000, category_id="mercado", order=3),
    )

    output = await summarize(repository, user_id)

    assert [(c.category_id, c.spent, c.count) for c in output.by_category] == [
        ("mercado", 400_000, 1),
        ("cafe", 15_000, 2),
    ]


@pytest.mark.asyncio
async def test_keeps_an_unclassified_bucket() -> None:
    """Spend without a category is a real state the assistant will want to flag."""
    user_id = new_user_id()
    repository = InMemoryMovementRepository(
        movement(user_id, amount=90_000, category_id=None),
        movement(user_id, amount=10_000, category_id="cafe", order=1),
    )

    output = await summarize(repository, user_id)

    assert output.by_category[0].category_id is None
    assert output.by_category[0].spent == 90_000


@pytest.mark.asyncio
async def test_only_counts_the_requested_range() -> None:
    user_id = new_user_id()
    repository = InMemoryMovementRepository(
        movement(user_id, amount=1_000, occurred_on="2026-06-30"),
        movement(user_id, amount=2_000, occurred_on="2026-07-01"),
        movement(user_id, amount=4_000, occurred_on="2026-07-31"),
        movement(user_id, amount=8_000, occurred_on="2026-08-01"),
    )

    output = await summarize(repository, user_id)

    assert output.expense_total == 6_000
    assert output.date_from == "2026-07-01"
    assert output.date_to == "2026-07-31"


@pytest.mark.asyncio
async def test_never_counts_another_tenant() -> None:
    user_id = new_user_id()
    repository = InMemoryMovementRepository(
        movement(user_id, amount=1_000),
        movement(new_user_id(), amount=999_000),
    )

    output = await summarize(repository, user_id)

    assert output.expense_total == 1_000
    assert output.count == 1


@pytest.mark.asyncio
async def test_rejects_a_bogus_range() -> None:
    with pytest.raises(InvalidMovementError):
        await summarize(InMemoryMovementRepository(), new_user_id(), ("julio", "2026-07-31"))
