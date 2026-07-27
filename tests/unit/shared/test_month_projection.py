"""The projection, tested at the primitive both modules call.

`overview` reaches it through `spending_pace` and `budgets` through `spending_cap`, so
the invariant is asserted here once: **what is projected is the month, not the month
plus today**. That off-by-one shipped, and it was caught by reading the card — $82.500
at $3.173/day was shown closing at $101.538 instead of $98.365, because `days_left`
includes today exactly like `days_elapsed` does.
"""

from src.shared.domain.month_projection import MIN_DAYS_FOR_PROJECTION, project

DAYS_IN_JULY = 31


def test_the_projection_is_the_daily_average_over_the_whole_month() -> None:
    projected = project(spent=82_500, days_elapsed=26, total_days=DAYS_IN_JULY)

    assert projected == 98_365  # about 3.173 x 31, not 101.538 (that was 32 days)
    assert abs(projected - (82_500 // 26) * DAYS_IN_JULY) <= DAYS_IN_JULY


def test_holding_back_can_never_raise_it() -> None:
    """A day passes with nothing spent: the projection falls. The allowance it
    replaced did the opposite."""
    day_10 = project(spent=1_000_000, days_elapsed=10, total_days=DAYS_IN_JULY)
    day_11 = project(spent=1_000_000, days_elapsed=11, total_days=DAYS_IN_JULY)

    assert day_10 is not None
    assert day_11 is not None
    assert day_11 < day_10


def test_it_carries_what_was_spent_and_estimates_only_the_rest() -> None:
    # 1.000.000 already spent + the 21 days that are left after today.
    assert project(spent=1_000_000, days_elapsed=10, total_days=DAYS_IN_JULY) == 3_100_000


def test_on_the_last_day_it_is_what_was_spent() -> None:
    """Nothing left to estimate: the month already happened."""
    assert project(spent=3_100_000, days_elapsed=DAYS_IN_JULY, total_days=DAYS_IN_JULY) == 3_100_000


def test_a_short_month_projects_over_its_own_length() -> None:
    assert project(spent=280_000, days_elapsed=14, total_days=28) == 560_000  # 20.000 x 28


def test_the_first_days_of_the_month_say_nothing() -> None:
    for day in range(1, MIN_DAYS_FOR_PROJECTION):
        assert project(spent=200_000, days_elapsed=day, total_days=DAYS_IN_JULY) is None


def test_a_month_without_spending_has_no_projection() -> None:
    """Zero divided over days is not information, it is a shrug."""
    assert project(spent=0, days_elapsed=15, total_days=DAYS_IN_JULY) is None
