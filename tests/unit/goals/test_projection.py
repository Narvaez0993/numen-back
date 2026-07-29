"""The pace projection — derived on every read, never stored.

The prototype persisted `projectionMonth: "octubre"`, wrong the month after it was
written. These tests pin the honest version: real pace, a floor of one month so a big
first week cannot promise a big month, and silence over alarm when there is nothing to
project from.
"""

from src.modules.goals.domain.projection import monthly_pace, needed_per_month, projected_on

TODAY = "2026-07-27"


def test_the_pace_is_saved_over_the_months_it_took() -> None:
    # 1.800.000 over 60 days = 900.000 a month.
    assert monthly_pace(saved=1_800_000, first_in_on="2026-05-28", today=TODAY) == 900_000


def test_the_first_week_cannot_promise_the_month() -> None:
    """$900.000 three days in is not a $9M monthly rhythm — the window floors at one
    month, so early paces read conservative instead of heroic."""
    assert monthly_pace(saved=900_000, first_in_on="2026-07-24", today=TODAY) == 900_000


def test_projection_lands_where_the_arithmetic_says() -> None:
    # 4.100.000 saved since end of May (~60 days) → pace 2.050.000; 7.900.000 to go
    # → 4 months (ceiling) → November 2026.
    result = projected_on(saved=4_100_000, target=12_000_000, first_in_on="2026-05-28", today=TODAY)
    assert result == "2026-11"


def test_projection_crosses_the_year_boundary() -> None:
    # Pace 100.000/month (floored window), 600.000 to go → 6 months from July → January.
    result = projected_on(saved=100_000, target=700_000, first_in_on="2026-07-20", today=TODAY)
    assert result == "2027-01"


def test_no_contributions_project_nothing() -> None:
    assert projected_on(saved=0, target=1_000_000, first_in_on=None, today=TODAY) is None


def test_a_reached_goal_projects_nothing() -> None:
    """The future already happened."""
    assert (
        projected_on(saved=1_000_000, target=1_000_000, first_in_on="2026-06-01", today=TODAY)
        is None
    )


def test_needed_per_month_spreads_what_is_left_over_the_months_left() -> None:
    # 7.900.000 to go, ~5 months to the date → ceiling 1.580.000.
    result = needed_per_month(
        saved=4_100_000, target=12_000_000, target_date="2026-12-27", today=TODAY
    )
    assert result == 1_580_000


def test_needed_per_month_without_a_date_is_silent() -> None:
    assert needed_per_month(saved=0, target=1_000_000, target_date=None, today=TODAY) is None


def test_a_deadline_behind_you_is_not_advice() -> None:
    assert (
        needed_per_month(saved=100_000, target=1_000_000, target_date="2026-07-01", today=TODAY)
        is None
    )


def test_the_last_stretch_asks_for_the_rest_in_one_month() -> None:
    """Twenty days out is less than a month, but the answer is still a monthly figure:
    everything that is left, this month."""
    result = needed_per_month(
        saved=900_000, target=1_000_000, target_date="2026-08-16", today=TODAY
    )
    assert result == 100_000
