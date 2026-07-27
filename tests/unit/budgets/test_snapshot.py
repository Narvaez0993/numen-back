"""The Presupuestos screen and the narrow read Home uses.

The one invariant that spans both: **the daily ceiling has to be the same number on both
screens**. That is why Home reads the cap through this module instead of dividing the
target itself, and the last test here is that assertion.
"""

import pytest

from src.modules.budgets.application.dto.budget_commands import (
    BudgetsSnapshotInputDTO,
    GlobalCapInputDTO,
)
from src.modules.budgets.application.use_cases.get_budgets_snapshot import (
    GetBudgetsSnapshotUseCase,
)
from src.modules.budgets.application.use_cases.get_global_cap import GetGlobalCapUseCase

from .fakes import (
    CURRENCY,
    DAYS_ELAPSED,
    DAYS_LEFT,
    TODAY,
    FakeBudgetRepository,
    FakeSpendReader,
    budget,
    merchant,
    new_user_id,
    spend,
)


async def snapshot(repository: FakeBudgetRepository, spending: FakeSpendReader, user_id):
    return await GetBudgetsSnapshotUseCase(
        budget_repository=repository, spend_reader=spending
    ).execute(BudgetsSnapshotInputDTO(user_id=user_id, currency=CURRENCY, today=TODAY))


async def global_cap(repository: FakeBudgetRepository, spending: FakeSpendReader, user_id):
    return await GetGlobalCapUseCase(budget_repository=repository, spend_reader=spending).execute(
        GlobalCapInputDTO(user_id=user_id, today=TODAY)
    )


@pytest.mark.asyncio
async def test_without_a_cap_the_screen_has_no_ceiling_to_show() -> None:
    """`null`, not a $0 target the user would appear to have blown on day one."""
    output = await snapshot(FakeBudgetRepository(), FakeSpendReader(), new_user_id())

    assert output.month is None
    assert output.categories == []
    assert output.period == "2026-07"
    assert output.days_left == DAYS_LEFT
    assert output.days_elapsed == DAYS_ELAPSED


@pytest.mark.asyncio
async def test_the_ceiling_is_measured_against_every_expense_of_the_month() -> None:
    user_id = new_user_id()
    repository = FakeBudgetRepository([budget(user_id=user_id, target=3_000_000)])
    spending = FakeSpendReader(
        by_category=[spend("mercado", 1_500_000, 9), spend(None, 419_500, 3)]
    )

    output = await snapshot(repository, spending, user_id)

    assert output.month is not None
    # The unclassified bucket counts too: it is spending, whatever it is called.
    assert output.month.spent == 1_919_500
    assert output.month.remaining == 1_080_500
    assert output.month.per_day == 1_080_500 // DAYS_LEFT


@pytest.mark.asyncio
async def test_only_watched_categories_are_computed() -> None:
    """Spending outside a cap is spending the user chose not to watch. Inventing a cap
    for it would be the app deciding for them."""
    user_id = new_user_id()
    repository = FakeBudgetRepository(
        [
            budget(user_id=user_id, target=3_000_000),
            budget(user_id=user_id, scope="category", category_id="mercado", target=400_000),
        ]
    )
    spending = FakeSpendReader(
        by_category=[spend("mercado", 356_000, 9), spend("transporte", 800_000, 12)]
    )

    output = await snapshot(repository, spending, user_id)

    assert [category.category_id for category in output.categories] == ["mercado"]
    assert output.categories[0].spent == 356_000
    assert output.categories[0].count == 9


@pytest.mark.asyncio
async def test_a_watched_category_with_no_expenses_is_zero_not_missing() -> None:
    user_id = new_user_id()
    repository = FakeBudgetRepository(
        [budget(user_id=user_id, scope="category", category_id="mercado", target=400_000)]
    )

    output = await snapshot(repository, FakeSpendReader(), user_id)

    assert len(output.categories) == 1
    assert output.categories[0].spent == 0
    assert output.categories[0].used == 0
    assert output.categories[0].per_day == 400_000 // DAYS_LEFT


@pytest.mark.asyncio
async def test_the_categories_come_ordered_by_urgency_not_by_size() -> None:
    """$95.000 of a $100.000 cap matters more than $500.000 of a $2.000.000 one."""
    user_id = new_user_id()
    repository = FakeBudgetRepository(
        [
            budget(user_id=user_id, scope="category", category_id="mercado", target=2_000_000),
            budget(user_id=user_id, scope="category", category_id="domicilios", target=100_000),
        ]
    )
    spending = FakeSpendReader(
        by_category=[spend("mercado", 500_000, 9), spend("domicilios", 95_000, 4)]
    )

    output = await snapshot(repository, spending, user_id)

    assert [category.category_id for category in output.categories] == ["domicilios", "mercado"]


@pytest.mark.asyncio
async def test_a_watched_category_carries_where_its_money_went() -> None:
    user_id = new_user_id()
    repository = FakeBudgetRepository(
        [budget(user_id=user_id, scope="category", category_id="mercado", target=400_000)]
    )
    spending = FakeSpendReader(
        by_category=[spend("mercado", 356_000, 9)],
        merchants={
            "mercado": [
                merchant("Exito", 180_000, 4),
                merchant("D1", 96_000, 3),
                merchant("Fruver Central", 80_000, 2),
            ]
        },
    )

    output = await snapshot(repository, spending, user_id)

    merchants = output.categories[0].top_merchants
    assert [m.label for m in merchants] == ["Exito", "D1", "Fruver Central"]
    assert merchants[0].spent == 180_000
    assert merchants[0].count == 4


@pytest.mark.asyncio
async def test_the_caps_are_not_additive() -> None:
    """A category cap warns about that category; every expense still counts against the
    ceiling. Summing them would invent a budget the user never set."""
    user_id = new_user_id()
    repository = FakeBudgetRepository(
        [
            budget(user_id=user_id, target=1_000_000),
            budget(user_id=user_id, scope="category", category_id="mercado", target=400_000),
        ]
    )
    spending = FakeSpendReader(by_category=[spend("mercado", 356_000, 9)])

    output = await snapshot(repository, spending, user_id)

    assert output.month is not None
    assert output.month.spent == 356_000  # the same peso, counted in both places
    assert output.categories[0].spent == 356_000
    assert output.month.target == 1_000_000


@pytest.mark.asyncio
async def test_home_reads_nothing_when_there_is_no_ceiling() -> None:
    user_id = new_user_id()
    repository = FakeBudgetRepository(
        [budget(user_id=user_id, scope="category", category_id="mercado", target=400_000)]
    )

    assert await global_cap(repository, FakeSpendReader(), user_id) is None


@pytest.mark.asyncio
async def test_home_and_the_screen_show_the_same_ceiling() -> None:
    """The reason Home does not do this arithmetic itself. Two implementations would
    drift, and the user would see $180.083 on one screen and $174.000 on the other."""
    user_id = new_user_id()
    repository = FakeBudgetRepository([budget(user_id=user_id, target=3_000_000)])
    rows = [spend("mercado", 1_500_000, 9), spend(None, 419_500, 3)]

    from_home = await global_cap(repository, FakeSpendReader(by_category=rows), user_id)
    from_screen = await snapshot(repository, FakeSpendReader(by_category=rows), user_id)

    assert from_home is not None
    assert from_screen.month is not None
    assert from_home.per_day == from_screen.month.per_day
    assert from_home.spent == from_screen.month.spent
    assert from_home.projected == from_screen.month.projected
    assert from_home.over == from_screen.month.over


@pytest.mark.asyncio
async def test_home_asks_only_about_the_month_it_needs() -> None:
    """One indexed document plus one aggregation: the narrow read exists so the hero does
    not pay for the per category work."""
    user_id = new_user_id()
    repository = FakeBudgetRepository([budget(user_id=user_id)])
    spending = FakeSpendReader(by_category=[spend("mercado", 100_000, 2)])

    await global_cap(repository, spending, user_id)

    assert spending.ranges == [("2026-07-01", "2026-07-31")]
