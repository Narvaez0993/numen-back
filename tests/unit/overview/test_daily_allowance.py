"""The ladder behind Home's hero — the rule that decides what the app promises.

Every case asserts `basis` as well as the number: showing a figure without saying
where it comes from is how a projection turns into invented advice.
"""

import pytest

from src.modules.overview.domain.daily_allowance import compute


def test_income_registered_derives_the_daily_figure() -> None:
    allowance = compute(spent=1_000_000, income=4_000_000, days_left=10)

    assert allowance.basis == "income"
    assert allowance.available == 300_000


def test_without_income_there_is_no_daily_figure() -> None:
    """No income and no budget means nothing to divide — better empty than invented."""
    allowance = compute(spent=500_000, income=0, days_left=10)

    assert allowance.basis == "none"
    assert allowance.available == 0


def test_spending_past_your_income_shows_a_negative() -> None:
    """The honest answer, not a zero that hides it."""
    allowance = compute(spent=5_000_000, income=4_000_000, days_left=10)

    assert allowance.basis == "income"
    assert allowance.available == -100_000


def test_a_budget_outranks_income() -> None:
    """Reserved for phase 3: the shape already accepts it."""
    allowance = compute(spent=1_000_000, income=4_000_000, days_left=10, budget=2_000_000)

    assert allowance.basis == "budget"
    assert allowance.available == 100_000


def test_a_zero_budget_falls_back_to_income() -> None:
    allowance = compute(spent=0, income=3_000_000, days_left=10, budget=0)

    assert allowance.basis == "income"


def test_the_last_day_of_the_month_divides_by_one() -> None:
    allowance = compute(spent=1_000_000, income=4_000_000, days_left=1)

    assert allowance.available == 3_000_000


@pytest.mark.parametrize("days_left", [0, -1])
def test_a_closed_month_has_no_daily_figure(days_left: int) -> None:
    """Guards the division; a month with no days left cannot suggest anything."""
    allowance = compute(spent=0, income=4_000_000, days_left=days_left)

    assert allowance.basis == "none"
    assert allowance.available == 0


def test_the_figure_is_floored_to_whole_minor_units() -> None:
    """Money is an integer in its minor unit — no fractional pesos anywhere."""
    allowance = compute(spent=0, income=100, days_left=3)

    assert allowance.available == 33
