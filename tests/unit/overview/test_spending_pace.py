"""The pace — and the two mistakes it has already made.

1. The figure it replaced was `(income - spent) / days_left`, which **grew every day the
   user held back**: the same money divided by fewer days. That is why the hero was
   rewritten, and it is the first test here.
2. Its own first version projected over `days_left`, which **includes today** — same as
   `days_elapsed`. A 31-day month was estimated as 32, and it was caught by reading the
   card: $82.500 at $3.173/day was shown closing at $101.538 instead of $98.365. The
   signature now takes the month's length so a caller cannot repeat it.
"""

import pytest

from src.modules.overview.domain.spending_pace import (
    MIN_DAYS_FOR_PROJECTION,
    change,
    compute,
)

DAYS_IN_JULY = 31


def test_holding_back_can_never_raise_the_projection() -> None:
    """A day passes with nothing spent: the projection must fall, never rise.

    The old allowance did the opposite — on the 31st it offered the whole remaining
    income for a single day.
    """
    day_10 = compute(spent=1_000_000, days_elapsed=10, total_days=DAYS_IN_JULY)
    day_11 = compute(spent=1_000_000, days_elapsed=11, total_days=DAYS_IN_JULY)

    assert day_10 is not None
    assert day_11 is not None
    assert day_11.projected < day_10.projected
    assert day_11.daily_average < day_10.daily_average


def test_the_projection_is_the_daily_average_over_the_whole_month() -> None:
    """The invariant that catches the off-by-one-day: what is projected is the month,
    not the month plus today."""
    pace = compute(spent=82_500, days_elapsed=26, total_days=DAYS_IN_JULY)

    assert pace is not None
    assert pace.daily_average == 3_173  # 82.500 / 26
    assert pace.projected == 98_365  # about 3.173 x 31, not 101.538 (that was 32 days)
    assert abs(pace.projected - pace.daily_average * DAYS_IN_JULY) <= DAYS_IN_JULY


def test_the_projection_carries_what_was_spent_and_estimates_only_the_rest() -> None:
    pace = compute(spent=1_000_000, days_elapsed=10, total_days=DAYS_IN_JULY)

    assert pace is not None
    assert pace.daily_average == 100_000
    # 1.000.000 already spent + the 21 days that are left after today.
    assert pace.projected == 1_000_000 + 2_100_000


def test_it_never_projects_below_what_is_already_spent() -> None:
    """The estimate cannot contradict the ledger."""
    pace = compute(spent=1_919_500, days_elapsed=26, total_days=DAYS_IN_JULY)

    assert pace is not None
    assert pace.projected >= 1_919_500


def test_on_the_last_day_the_projection_is_what_was_spent() -> None:
    """Nothing left to estimate: the month already happened."""
    pace = compute(spent=3_100_000, days_elapsed=DAYS_IN_JULY, total_days=DAYS_IN_JULY)

    assert pace is not None
    assert pace.daily_average == 100_000
    assert pace.projected == 3_100_000


def test_the_first_days_of_the_month_say_nothing() -> None:
    """One restaurant bill on the 2nd would forecast a month of eating out."""
    for day in range(1, MIN_DAYS_FOR_PROJECTION):
        assert compute(spent=200_000, days_elapsed=day, total_days=DAYS_IN_JULY) is None


def test_from_the_third_day_it_projects() -> None:
    assert (
        compute(spent=200_000, days_elapsed=MIN_DAYS_FOR_PROJECTION, total_days=DAYS_IN_JULY)
        is not None
    )


def test_a_month_without_spending_has_no_pace() -> None:
    """Zero divided over days is not information, it is a shrug."""
    assert compute(spent=0, days_elapsed=15, total_days=DAYS_IN_JULY) is None


def test_a_short_month_projects_over_its_own_length() -> None:
    february = compute(spent=280_000, days_elapsed=14, total_days=28)

    assert february is not None
    assert february.daily_average == 20_000
    assert february.projected == 560_000  # 20.000 x 28


def test_change_is_signed_against_the_same_stretch() -> None:
    assert change(1_919_500, 2_181_000) == pytest.approx(-0.1199, abs=0.001)
    assert change(2_400_000, 2_000_000) == pytest.approx(0.2, abs=0.001)


def test_change_needs_something_to_compare_against() -> None:
    """A first month has no trend, and a 0 would read as "you spent the same"."""
    assert change(1_919_500, 0) is None
