from datetime import timedelta
from uuid import UUID

import pytest

from src.modules.movements.application.dto.list_movements import ListMovementsInputDTO
from src.modules.movements.application.use_cases.list_movements import ListMovementsUseCase
from src.modules.movements.domain.entities.movement import Movement, SourceRef
from src.modules.movements.domain.errors import InvalidMovementError

from .fakes import CURRENCY, FIXED_NOW, InMemoryMovementRepository, new_user_id


def movement(
    user_id: UUID,
    *,
    occurred_on: str,
    type: str = "expense",
    source_id: str = "nequi",
    destination_id: str | None = None,
    category_id: str | None = "cafe",
    order: int = 0,
) -> Movement:
    return Movement(
        id=f"mov-{occurred_on}-{source_id}-{order}",
        user_id=user_id,
        type=type,  # type: ignore[arg-type]
        description="Café",
        amount=12_000,
        currency=CURRENCY,
        source=SourceRef(type="account", id=source_id),
        destination=(
            None if destination_id is None else SourceRef(type="account", id=destination_id)
        ),
        category_id=category_id,
        occurred_on=occurred_on,
        captured_via="manual",
        created_at=FIXED_NOW + timedelta(minutes=order),
    )


@pytest.mark.asyncio
async def test_lists_only_the_callers_movements() -> None:
    user_id = new_user_id()
    other_id = new_user_id()
    repository = InMemoryMovementRepository(
        movement(user_id, occurred_on="2026-07-10"),
        movement(other_id, occurred_on="2026-07-11"),
    )
    use_case = ListMovementsUseCase(movement_repository=repository)

    output = await use_case.execute(ListMovementsInputDTO(user_id=user_id))

    assert len(output.movements) == 1


@pytest.mark.asyncio
async def test_filters_by_month_range() -> None:
    user_id = new_user_id()
    repository = InMemoryMovementRepository(
        movement(user_id, occurred_on="2026-06-30"),
        movement(user_id, occurred_on="2026-07-01"),
        movement(user_id, occurred_on="2026-07-31"),
        movement(user_id, occurred_on="2026-08-01"),
    )
    use_case = ListMovementsUseCase(movement_repository=repository)

    output = await use_case.execute(
        ListMovementsInputDTO(user_id=user_id, date_from="2026-07-01", date_to="2026-07-31")
    )

    assert [m.occurred_on for m in output.movements] == ["2026-07-31", "2026-07-01"]


@pytest.mark.asyncio
async def test_orders_newest_first_and_breaks_ties_by_creation() -> None:
    user_id = new_user_id()
    repository = InMemoryMovementRepository(
        movement(user_id, occurred_on="2026-07-10", order=1),
        movement(user_id, occurred_on="2026-07-10", order=2),
        movement(user_id, occurred_on="2026-07-12", order=0),
    )
    use_case = ListMovementsUseCase(movement_repository=repository)

    output = await use_case.execute(ListMovementsInputDTO(user_id=user_id))

    assert [m.occurred_on for m in output.movements] == [
        "2026-07-12",
        "2026-07-10",
        "2026-07-10",
    ]
    assert output.movements[1].id.endswith("-2")


@pytest.mark.asyncio
async def test_filters_by_type() -> None:
    user_id = new_user_id()
    repository = InMemoryMovementRepository(
        movement(user_id, occurred_on="2026-07-10", type="expense"),
        movement(user_id, occurred_on="2026-07-11", type="income", category_id="salario"),
    )
    use_case = ListMovementsUseCase(movement_repository=repository)

    output = await use_case.execute(ListMovementsInputDTO(user_id=user_id, type="income"))

    assert [m.type for m in output.movements] == ["income"]


@pytest.mark.asyncio
async def test_filters_by_category() -> None:
    user_id = new_user_id()
    repository = InMemoryMovementRepository(
        movement(user_id, occurred_on="2026-07-10", category_id="cafe"),
        movement(user_id, occurred_on="2026-07-11", category_id="mercado"),
    )
    use_case = ListMovementsUseCase(movement_repository=repository)

    output = await use_case.execute(ListMovementsInputDTO(user_id=user_id, category_id="mercado"))

    assert [m.category_id for m in output.movements] == ["mercado"]


@pytest.mark.asyncio
async def test_a_source_filter_matches_both_ends_of_a_transfer() -> None:
    """Filtering by "banco" must show money that arrived there, not just left it."""
    user_id = new_user_id()
    repository = InMemoryMovementRepository(
        movement(user_id, occurred_on="2026-07-10", source_id="nequi"),
        movement(
            user_id,
            occurred_on="2026-07-11",
            type="transfer",
            source_id="nequi",
            destination_id="banco",
            category_id=None,
        ),
    )
    use_case = ListMovementsUseCase(movement_repository=repository)

    output = await use_case.execute(ListMovementsInputDTO(user_id=user_id, source_id="banco"))

    assert [m.type for m in output.movements] == ["transfer"]


@pytest.mark.asyncio
async def test_the_limit_is_clamped_to_a_sane_range() -> None:
    user_id = new_user_id()
    repository = InMemoryMovementRepository(
        *[movement(user_id, occurred_on="2026-07-10", order=i) for i in range(5)]
    )
    use_case = ListMovementsUseCase(movement_repository=repository)

    assert (
        len((await use_case.execute(ListMovementsInputDTO(user_id=user_id, limit=2))).movements)
        == 2
    )
    assert (
        len((await use_case.execute(ListMovementsInputDTO(user_id=user_id, limit=0))).movements)
        == 1
    )
    assert (
        len((await use_case.execute(ListMovementsInputDTO(user_id=user_id, limit=999))).movements)
        == 5
    )


@pytest.mark.asyncio
async def test_rejects_a_bogus_date_bound() -> None:
    use_case = ListMovementsUseCase(movement_repository=InMemoryMovementRepository())

    with pytest.raises(InvalidMovementError):
        await use_case.execute(ListMovementsInputDTO(user_id=new_user_id(), date_from="julio"))
