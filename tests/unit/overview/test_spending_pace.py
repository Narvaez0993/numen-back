"""The pace — and the property the old daily allowance violated.

The figure it replaced was `(income - spent) / days_left`, which **grew every day the
user held back**: the same money divided by fewer days. The first test here is the one
that matters, because it is the reason the hero was rewritten.
"""

import pytest

from src.modules.overview.domain.spending_pace import (
    MIN_DAYS_FOR_PROJECTION,
    change,
    compute,
)


def test_holding_back_can_never_raise_the_projection() -> None:
    """A day passes with nothing spent: the projection must fall, never rise.

    The old allowance did the opposite — on the 31st it offered the whole remaining
    income for a single day.
    """
    day_10 = compute(spent=1_000_000, days_elapsed=10, days_left=21)
    day_11 = compute(spent=1_000_000, days_elapsed=11, days_left=20)

    assert day_10 is not None
    assert day_11 is not None
    assert day_11.projected < day_10.projected
    assert day_11.daily_average < day_10.daily_average


def test_the_projection_carries_what_was_spent_and_estimates_only_the_rest() -> None:
    pace = compute(spent=1_000_000, days_elapsed=10, days_left=21)

    assert pace is not None
    assert pace.daily_average == 100_000
    # 1.000.000 already spent + 21 days at that rate.
    assert pace.projected == 1_000_000 + 2_100_000


def test_it_never_projects_below_what_is_already_spent() -> None:
    """The estimate cannot contradict the ledger."""
    pace = compute(spent=1_919_500, days_elapsed=26, days_left=6)

    assert pace is not None
    assert pace.projected >= 1_919_500


def test_the_first_days_of_the_month_say_nothing() -> None:
    """One restaurant bill on the 2nd would forecast a month of eating out."""
    for day in range(1, MIN_DAYS_FOR_PROJECTION):
        assert compute(spent=200_000, days_elapsed=day, days_left=31 - day) is None


def test_from_the_third_day_it_projects() -> None:
    assert compute(spent=200_000, days_elapsed=MIN_DAYS_FOR_PROJECTION, days_left=28) is not None


def test_a_month_without_spending_has_no_pace() -> None:
    """Zero divided over days is not information, it is a shrug."""
    assert compute(spent=0, days_elapsed=15, days_left=16) is None


def test_the_last_day_of_the_month_projects_one_more_day() -> None:
    pace = compute(spent=3_100_000, days_elapsed=31, days_left=1)

    assert pace is not None
    assert pace.daily_average == 100_000
    assert pace.projected == 3_200_000


def test_change_is_signed_against_the_same_stretch() -> None:
    assert change(1_919_500, 2_181_000) == pytest.approx(-0.1199, abs=0.001)
    assert change(2_400_000, 2_000_000) == pytest.approx(0.2, abs=0.001)


def test_change_needs_something_to_compare_against() -> None:
    """A first month has no trend, and a 0 would read as "you spent the same"."""
    assert change(1_919_500, 0) is None
