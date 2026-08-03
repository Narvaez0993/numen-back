"""When the money moved — the day-by-day rhythm the Corte's fun fact reads."""

from datetime import timedelta
from uuid import UUID

import pytest

from src.modules.movements.application.dto.daily_spend import DailySpendInputDTO
from src.modules.movements.application.use_cases.get_daily_spend import GetDailySpendUseCase
from src.modules.movements.domain.entities.movement import Movement, SourceRef
from src.modules.movements.domain.errors import InvalidMovementError

from .fakes import CURRENCY, FIXED_NOW, InMemoryMovementRepository, new_user_id

JULY = ("2026-07-01", "2026-07-31")


def movement(
    user_id: UUID,
    *,
    type: str = "expense",
    amount: int = 10_000,
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
        category_id=None if type == "transfer" else "cafe",
        occurred_on=occurred_on,
        captured_via="manual",
        created_at=FIXED_NOW + timedelta(minutes=order),
    )


async def daily(repository: InMemoryMovementRepository, user_id: UUID):
    return await GetDailySpendUseCase(movement_repository=repository).execute(
        DailySpendInputDTO(user_id=user_id, date_from=JULY[0], date_to=JULY[1])
    )


@pytest.mark.asyncio
async def test_groups_expenses_by_day_chronologically() -> None:
    user_id = new_user_id()
    repository = InMemoryMovementRepository(
        movement(user_id, amount=30_000, occurred_on="2026-07-18"),
        movement(user_id, amount=20_000, occurred_on="2026-07-18", order=1),
        movement(user_id, amount=10_000, occurred_on="2026-07-03"),
    )

    output = await daily(repository, user_id)

    assert [(d.day, d.spent, d.count) for d in output.days] == [
        ("2026-07-03", 10_000, 1),
        ("2026-07-18", 50_000, 2),
    ]


@pytest.mark.asyncio
async def test_income_and_transfers_do_not_count() -> None:
    user_id = new_user_id()
    repository = InMemoryMovementRepository(
        movement(user_id, type="income", amount=4_000_000),
        movement(user_id, type="transfer", amount=100_000),
        movement(user_id, amount=15_000),
    )

    output = await daily(repository, user_id)

    assert [(d.day, d.spent) for d in output.days] == [("2026-07-10", 15_000)]


@pytest.mark.asyncio
async def test_rejects_malformed_dates() -> None:
    with pytest.raises(InvalidMovementError):
        await GetDailySpendUseCase(movement_repository=InMemoryMovementRepository()).execute(
            DailySpendInputDTO(user_id=new_user_id(), date_from="julio", date_to=JULY[1])
        )
