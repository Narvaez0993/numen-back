import pytest

from src.modules.overview.application.dto.home_overview import HomeOverviewInputDTO
from src.modules.overview.application.ports.movement_summary_reader import PeriodSummary
from src.modules.overview.application.use_cases.get_home_overview import (
    GetHomeOverviewUseCase,
)

from .fakes import (
    CURRENCY,
    FakeBalanceReader,
    FakeBudgetReader,
    FakeDebtReader,
    FakeGoalReader,
    FakeMovementSummaryReader,
    FakeUpcomingChargesReader,
    debt_totals,
    global_cap,
    new_user_id,
    recent_movement,
    spend,
    upcoming_charge,
)

# 26 July 2026 → 26 days elapsed, 6 left (26th through 31st).
TODAY = "2026-07-26"
DAYS_LEFT = 6
DAYS_ELAPSED = 26
TOTAL_DAYS = 31


def build(
    *,
    balance: FakeBalanceReader | None = None,
    summaries: FakeMovementSummaryReader | None = None,
    charges: FakeUpcomingChargesReader | None = None,
    budgets: FakeBudgetReader | None = None,
    debts: FakeDebtReader | None = None,
    goals: FakeGoalReader | None = None,
) -> GetHomeOverviewUseCase:
    return GetHomeOverviewUseCase(
        balance_reader=balance or FakeBalanceReader(),
        movement_summary_reader=summaries or FakeMovementSummaryReader(),
        upcoming_charges_reader=charges or FakeUpcomingChargesReader(),
        budget_reader=budgets or FakeBudgetReader(),
        debt_reader=debts or FakeDebtReader(),
        goal_reader=goals or FakeGoalReader(),
    )


async def overview(
    use_case: GetHomeOverviewUseCase,
    today: str = TODAY,
    objective: str | None = None,
):
    return await use_case.execute(
        HomeOverviewInputDTO(
            user_id=new_user_id(), currency=CURRENCY, today=today, objective=objective
        )
    )


@pytest.mark.asyncio
async def test_a_brand_new_user_gets_the_checklist_and_no_figures() -> None:
    output = await overview(build())

    assert output.focus == "start"
    assert output.pace is None
    assert output.month.spent == 0
    assert output.month.previous is None
    assert output.month.change is None
    assert output.top_categories == []
    assert output.recent == []


@pytest.mark.asyncio
async def test_registering_movements_turns_on_the_pace() -> None:
    summaries = FakeMovementSummaryReader(month=PeriodSummary(expense_total=1_919_500, count=12))

    output = await overview(build(summaries=summaries))

    assert output.focus == "pace"
    assert output.pace is not None
    assert output.pace.daily_average == 1_919_500 // DAYS_ELAPSED
    # Projected over the 5 days left **after** today, not the 6 the label counts:
    # `days_elapsed` and `days_left` both include today, so adding them would make
    # July 32 days long.
    assert (
        output.pace.projected == 1_919_500 + 1_919_500 * (TOTAL_DAYS - DAYS_ELAPSED) // DAYS_ELAPSED
    )


@pytest.mark.asyncio
async def test_there_is_no_daily_allowance_anywhere_in_the_payload() -> None:
    """The figure that answered "how much may I spend today" is gone on purpose: it was
    a permission the app has no business granting, and it grew when the user held back.
    """
    summaries = FakeMovementSummaryReader(
        month=PeriodSummary(expense_total=1_000_000, income_total=5_000_000, count=8)
    )

    output = await overview(build(summaries=summaries))

    assert not hasattr(output, "daily")
    assert "available" not in output.model_dump()


@pytest.mark.asyncio
async def test_the_month_is_compared_against_the_same_stretch_of_the_last_one() -> None:
    summaries = FakeMovementSummaryReader(
        month=PeriodSummary(expense_total=1_919_500, count=12),
        previous=PeriodSummary(expense_total=2_181_000, income_total=5_000_000, count=15),
    )

    output = await overview(build(summaries=summaries))

    assert output.month.previous is not None
    assert output.month.previous.spent == 2_181_000
    assert output.month.change == pytest.approx(-0.1199, abs=0.001)
    # month range, today, and last month cut at the same day.
    assert summaries.ranges == [
        ("2026-07-01", "2026-07-31"),
        (TODAY, TODAY),
        ("2026-06-01", "2026-06-26"),
    ]


@pytest.mark.asyncio
async def test_a_first_month_has_no_trend_instead_of_a_zero() -> None:
    summaries = FakeMovementSummaryReader(month=PeriodSummary(expense_total=500_000, count=3))

    output = await overview(build(summaries=summaries))

    assert output.month.previous is None
    assert output.month.change is None


@pytest.mark.asyncio
async def test_what_was_saved_travels_as_a_figure_of_its_own() -> None:
    summaries = FakeMovementSummaryReader(
        month=PeriodSummary(expense_total=1_919_500, income_total=5_000_000, count=12)
    )

    output = await overview(build(summaries=summaries), objective="ahorrar")

    assert output.focus == "saving"
    assert output.month.saved == 5_000_000 - 1_919_500
    assert output.month.savings_rate == pytest.approx(0.616, abs=0.001)


@pytest.mark.asyncio
async def test_the_debt_objective_leads_with_the_card_debt() -> None:
    balance = FakeBalanceReader(card_debt=830_900, card_limit=5_000_000, credit_cards_count=1)
    summaries = FakeMovementSummaryReader(month=PeriodSummary(expense_total=100_000, count=2))

    output = await overview(build(balance=balance, summaries=summaries), objective="deudas")

    assert output.focus == "debt"
    assert (output.card_debt, output.card_limit) == (830_900, 5_000_000)


@pytest.mark.asyncio
async def test_personal_debt_completes_the_debt_rung() -> None:
    """The rung used to know only about cards; owing a person now counts too, and the
    totals travel for the face's breakdown."""
    summaries = FakeMovementSummaryReader(month=PeriodSummary(expense_total=100_000, count=2))
    debts = FakeDebtReader(debt_totals(i_owe=200_000, owed_to_me=150_000, open_count=3))

    output = await overview(build(summaries=summaries, debts=debts), objective="deudas")

    assert output.focus == "debt"
    assert output.debts.i_owe == 200_000
    assert output.debts.owed_to_me == 150_000
    assert output.debts.open_count == 3


@pytest.mark.asyncio
async def test_owing_nobody_is_a_measurement_not_a_missing_block() -> None:
    output = await overview(build())

    assert output.debts.i_owe == 0
    assert output.debts.owed_to_me == 0
    assert output.debts.open_count == 0


@pytest.mark.asyncio
async def test_an_objective_without_its_data_asks_for_it() -> None:
    summaries = FakeMovementSummaryReader(month=PeriodSummary(expense_total=100_000, count=2))

    output = await overview(build(summaries=summaries), objective="deudas")

    # No card debt AND nothing owed to people — only then does the hero ask.
    assert output.focus == "invite"
    assert output.objective == "deudas"
    # The pace still travels, so the client can show it under the invitation.
    assert output.pace is not None


@pytest.mark.asyncio
async def test_a_cap_leads_the_hero_and_brings_the_only_daily_figure() -> None:
    summaries = FakeMovementSummaryReader(month=PeriodSummary(expense_total=1_919_500, count=12))

    output = await overview(build(summaries=summaries, budgets=FakeBudgetReader(global_cap())))

    assert output.focus == "budget"
    assert output.budget is not None
    assert output.budget.target == 3_000_000
    assert output.budget.per_day == 180_083
    # The pace is still there: the cap face shows the projection next to the ceiling.
    assert output.pace is not None


@pytest.mark.asyncio
async def test_the_cap_travels_even_when_the_objective_leads() -> None:
    """A declared objective wins the hero, but the client keeps the cap as a secondary
    row — so it must be in the payload regardless of `focus`."""
    summaries = FakeMovementSummaryReader(month=PeriodSummary(expense_total=1_919_500, count=12))

    output = await overview(
        build(
            summaries=summaries,
            balance=FakeBalanceReader(card_debt=830_900, card_limit=5_000_000),
            budgets=FakeBudgetReader(global_cap()),
        ),
        objective="deudas",
    )

    assert output.focus == "debt"
    assert output.budget is not None


@pytest.mark.asyncio
async def test_without_a_cap_there_is_no_daily_figure_at_all() -> None:
    """The rule the allowance broke: a daily number only exists when it comes from a
    ceiling the user chose."""
    summaries = FakeMovementSummaryReader(month=PeriodSummary(expense_total=1_919_500, count=12))

    output = await overview(build(summaries=summaries))

    assert output.focus == "pace"
    assert output.budget is None
    assert "per_day" not in output.model_dump(exclude={"budget"})


@pytest.mark.asyncio
async def test_the_cap_is_asked_for_the_clients_day() -> None:
    """The ceiling divides by the days left, so reading it with the server's day would
    hand the wrong number to anyone far from UTC."""
    budgets = FakeBudgetReader(global_cap())

    await overview(build(budgets=budgets), today="2026-02-10")

    assert budgets.days == ["2026-02-10"]


@pytest.mark.asyncio
async def test_the_period_and_the_days_come_from_the_clients_day() -> None:
    output = await overview(build(), today="2026-02-10")

    assert output.period == "2026-02"
    assert output.days_left == 19  # 10th through 28th
    assert output.days_elapsed == 10


@pytest.mark.asyncio
async def test_the_comparable_stretch_clamps_to_a_shorter_month() -> None:
    """The 31st of March compares against the 28th of February, not the 3rd of March."""
    summaries = FakeMovementSummaryReader(month_key="2026-03")

    await overview(build(summaries=summaries), today="2026-03-31")

    assert summaries.ranges[2] == ("2026-02-01", "2026-02-28")


@pytest.mark.asyncio
async def test_top_categories_carry_their_share_of_the_month() -> None:
    summaries = FakeMovementSummaryReader(
        month=PeriodSummary(
            expense_total=1_000_000,
            count=14,
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
async def test_top_categories_are_capped() -> None:
    summaries = FakeMovementSummaryReader(
        month=PeriodSummary(
            expense_total=500_000,
            count=8,
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
async def test_recent_movements_alone_are_enough_to_leave_the_checklist() -> None:
    """A movement from last month still means the user has registered money."""
    summaries = FakeMovementSummaryReader(recent=[recent_movement()])

    output = await overview(build(summaries=summaries))

    assert output.focus == "pace"


@pytest.mark.asyncio
async def test_the_position_comes_from_the_accounts_module() -> None:
    balance = FakeBalanceReader(
        net_balance=4_395_000, accounts_count=3, credit_cards_count=1, card_debt=830_900
    )

    output = await overview(build(balance=balance))

    assert output.net_balance == 4_395_000
    assert (output.accounts_count, output.credit_cards_count) == (3, 1)
    assert output.currency == CURRENCY


@pytest.mark.asyncio
async def test_upcoming_charges_look_a_week_ahead() -> None:
    charges = FakeUpcomingChargesReader()

    await overview(build(charges=charges))

    assert charges.windows == [(TODAY, "2026-08-02", 5)]


@pytest.mark.asyncio
async def test_upcoming_charges_travel_as_references_with_their_state() -> None:
    charges = FakeUpcomingChargesReader(
        [
            upcoming_charge(status="pending", charge_id="chg-1", charge_on=TODAY),
            upcoming_charge(subscription_id="gym", charge_on="2026-07-29"),
        ]
    )

    output = await overview(build(charges=charges))

    assert [(c.subscription_id, c.status, c.charge_id) for c in output.upcoming] == [
        ("netflix", "pending", "chg-1"),
        ("gym", "scheduled", None),
    ]
    assert not hasattr(output.upcoming[0], "name")


@pytest.mark.asyncio
async def test_the_pocket_leads_the_saving_face() -> None:
    from .fakes import top_goal

    summaries = FakeMovementSummaryReader(month=PeriodSummary(expense_total=100_000, count=2))

    output = await overview(
        build(summaries=summaries, goals=FakeGoalReader(top_goal())), objective="ahorrar"
    )

    assert output.focus == "saving"
    assert output.goal is not None
    assert output.goal.name == "Viaje a Japón"
    assert output.goal.saved == 4_100_000


@pytest.mark.asyncio
async def test_no_pocket_is_null_not_zeros() -> None:
    output = await overview(build())

    assert output.goal is None
