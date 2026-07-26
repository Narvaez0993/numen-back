import pytest

from src.modules.overview.application.dto.home_overview import HomeOverviewInputDTO
from src.modules.overview.application.ports.movement_summary_reader import PeriodSummary
from src.modules.overview.application.use_cases.get_home_overview import (
    GetHomeOverviewUseCase,
)

from .fakes import (
    CURRENCY,
    FakeBalanceReader,
    FakeMovementSummaryReader,
    new_user_id,
    recent_movement,
    spend,
)

# 25 July 2026 → 7 days left in the month (25th through 31st).
TODAY = "2026-07-25"
DAYS_LEFT = 7


def build(
    *,
    balance: FakeBalanceReader | None = None,
    summaries: FakeMovementSummaryReader | None = None,
) -> GetHomeOverviewUseCase:
    return GetHomeOverviewUseCase(
        balance_reader=balance or FakeBalanceReader(),
        movement_summary_reader=summaries or FakeMovementSummaryReader(),
    )


async def overview(use_case: GetHomeOverviewUseCase, today: str = TODAY):
    return await use_case.execute(
        HomeOverviewInputDTO(user_id=new_user_id(), currency=CURRENCY, today=today)
    )


@pytest.mark.asyncio
async def test_a_brand_new_user_sees_zeros_and_no_daily_figure() -> None:
    output = await overview(build())

    assert output.net_balance == 0
    assert output.month.spent == 0
    assert output.month.savings_rate == 0.0
    assert output.daily.basis == "none"
    assert output.daily.available == 0
    assert output.top_categories == []
    assert output.recent == []


@pytest.mark.asyncio
async def test_only_expenses_still_leaves_the_daily_figure_empty() -> None:
    """Registering spending does not conjure a budget out of nowhere."""
    summaries = FakeMovementSummaryReader(month=PeriodSummary(expense_total=1_900_000, count=12))

    output = await overview(build(summaries=summaries))

    assert output.month.spent == 1_900_000
    assert output.month.movements == 12
    assert output.daily.basis == "none"


@pytest.mark.asyncio
async def test_registering_income_turns_on_the_daily_figure() -> None:
    summaries = FakeMovementSummaryReader(
        month=PeriodSummary(expense_total=1_000_000, income_total=4_000_000, count=13)
    )

    output = await overview(build(summaries=summaries))

    assert output.daily.basis == "income"
    assert output.daily.available == (4_000_000 - 1_000_000) // DAYS_LEFT
    assert output.month.savings_rate == pytest.approx(0.75)


@pytest.mark.asyncio
async def test_today_is_read_as_its_own_range() -> None:
    summaries = FakeMovementSummaryReader(
        month=PeriodSummary(expense_total=1_000_000, income_total=4_000_000),
        today=PeriodSummary(expense_total=45_000, count=2),
    )

    output = await overview(build(summaries=summaries))

    assert output.daily.spent_today == 45_000
    # The month range and the single day, in that order.
    assert summaries.ranges == [("2026-07-01", "2026-07-31"), (TODAY, TODAY)]


@pytest.mark.asyncio
async def test_the_period_and_days_left_come_from_the_clients_day() -> None:
    output = await overview(build(), today="2026-02-10")

    assert output.period == "2026-02"
    assert output.days_left == 19  # 10th through 28th


@pytest.mark.asyncio
async def test_the_last_day_of_the_month_still_has_one_day_left() -> None:
    output = await overview(build(), today="2026-07-31")

    assert output.days_left == 1


@pytest.mark.asyncio
async def test_a_leap_february_counts_the_extra_day() -> None:
    output = await overview(build(), today="2028-02-27")

    assert output.days_left == 3  # 27, 28, 29


@pytest.mark.asyncio
async def test_top_categories_carry_their_share_of_the_month() -> None:
    summaries = FakeMovementSummaryReader(
        month=PeriodSummary(
            expense_total=1_000_000,
            by_category=(
                spend("mercado", 600_000, 4),
                spend("cafe", 300_000, 9),
                spend(None, 100_000, 1),
            ),
        )
    )

    output = await overview(build(summaries=summaries))

    assert [(c.category_id, c.share) for c in output.top_categories] == [
        ("mercado", 0.6),
        ("cafe", 0.3),
        (None, 0.1),
    ]


@pytest.mark.asyncio
async def test_shares_are_zero_when_nothing_was_spent() -> None:
    """Guards the division; a category with 0 spend cannot have a share."""
    summaries = FakeMovementSummaryReader(
        month=PeriodSummary(expense_total=0, by_category=(spend("mercado", 0),))
    )

    output = await overview(build(summaries=summaries))

    assert output.top_categories[0].share == 0.0


@pytest.mark.asyncio
async def test_top_categories_are_capped() -> None:
    summaries = FakeMovementSummaryReader(
        month=PeriodSummary(
            expense_total=500_000,
            by_category=tuple(spend(f"cat-{i}", 100_000) for i in range(8)),
        )
    )

    output = await overview(build(summaries=summaries))

    assert len(output.top_categories) == 4


@pytest.mark.asyncio
async def test_recent_movements_travel_as_references_only() -> None:
    """No denormalized names: renaming a category updates Home for free."""
    summaries = FakeMovementSummaryReader(
        recent=[recent_movement(id="a"), recent_movement(id="b", type="income")]
    )

    output = await overview(build(summaries=summaries))

    assert [m.id for m in output.recent] == ["a", "b"]
    assert output.recent[0].category_id == "cafe"
    assert not hasattr(output.recent[0], "category_name")


@pytest.mark.asyncio
async def test_the_position_comes_from_the_accounts_module() -> None:
    balance = FakeBalanceReader(net_balance=4_395_000, accounts_count=3, credit_cards_count=1)

    output = await overview(build(balance=balance))

    assert output.net_balance == 4_395_000
    assert (output.accounts_count, output.credit_cards_count) == (3, 1)
    assert output.currency == CURRENCY
