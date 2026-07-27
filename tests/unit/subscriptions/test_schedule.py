"""The cadence rule. Calendars are where recurring charges usually go wrong.

Two properties are worth stating out loud, because both are easy to get wrong and
neither is visible until months later:

- monthly **clamps and recovers**: the 31st becomes the 28th in February and is the
  31st again in March — it does not drag down forever;
- monthly **never rolls over** into the next month (Feb 31 → Mar 3 would move the
  charge to a month the user did not pick).
"""

from src.modules.subscriptions.domain.schedule import (
    monthly_equivalent,
    next_charge_on,
    occurrences,
    yearly_equivalent,
)

from .fakes import subscription


def test_a_monthly_charge_repeats_on_the_same_day() -> None:
    sub = subscription(frequency="monthly", first_charge_on="2026-01-05")

    assert occurrences(sub, "2026-01-01", "2026-04-30") == [
        "2026-01-05",
        "2026-02-05",
        "2026-03-05",
        "2026-04-05",
    ]


def test_the_31st_clamps_to_the_end_of_a_short_month_and_comes_back() -> None:
    sub = subscription(frequency="monthly", first_charge_on="2026-01-31")

    assert occurrences(sub, "2026-01-01", "2026-04-30") == [
        "2026-01-31",
        "2026-02-28",  # clamped
        "2026-03-31",  # recovered, because every date is shifted from the anchor
        "2026-04-30",  # clamped again
    ]


def test_february_of_a_leap_year_gets_the_29th() -> None:
    sub = subscription(frequency="monthly", first_charge_on="2028-01-31")

    assert occurrences(sub, "2028-02-01", "2028-02-29") == ["2028-02-29"]


def test_a_weekly_charge_can_hit_several_times_in_one_month() -> None:
    sub = subscription(frequency="weekly", first_charge_on="2026-07-02")

    assert occurrences(sub, "2026-07-01", "2026-07-31") == [
        "2026-07-02",
        "2026-07-09",
        "2026-07-16",
        "2026-07-23",
        "2026-07-30",
    ]


def test_a_yearly_charge_appears_once_a_year() -> None:
    sub = subscription(frequency="yearly", first_charge_on="2026-03-15")

    assert occurrences(sub, "2026-01-01", "2028-12-31") == [
        "2026-03-15",
        "2027-03-15",
        "2028-03-15",
    ]


def test_nothing_is_owed_before_the_anchor() -> None:
    """A subscription registered today did not charge last month."""
    sub = subscription(frequency="monthly", first_charge_on="2026-07-10")

    assert occurrences(sub, "2026-05-01", "2026-06-30") == []


def test_a_paused_subscription_has_no_charge_dates() -> None:
    sub = subscription(first_charge_on="2026-07-01", active=False)

    assert occurrences(sub, "2026-07-01", "2026-07-31") == []
    assert occurrences(sub, "2026-07-01", "2026-07-31", include_paused=True) == ["2026-07-01"]
    assert next_charge_on(sub, "2026-07-01") is None


def test_the_next_charge_is_today_when_it_falls_today() -> None:
    """The due date counts as upcoming: that is the day it must be confirmed."""
    sub = subscription(frequency="monthly", first_charge_on="2026-01-26")

    assert next_charge_on(sub, "2026-07-26") == "2026-07-26"


def test_the_next_charge_skips_the_ones_already_past() -> None:
    sub = subscription(frequency="monthly", first_charge_on="2026-01-05")

    assert next_charge_on(sub, "2026-07-26") == "2026-08-05"


def test_a_future_anchor_is_its_own_next_charge() -> None:
    sub = subscription(frequency="monthly", first_charge_on="2026-09-01")

    assert next_charge_on(sub, "2026-07-26") == "2026-09-01"


def test_the_next_weekly_charge_lands_on_the_same_weekday() -> None:
    sub = subscription(frequency="weekly", first_charge_on="2026-07-02")

    assert next_charge_on(sub, "2026-07-26") == "2026-07-30"


def test_a_weekly_anchor_exactly_today_is_today() -> None:
    sub = subscription(frequency="weekly", first_charge_on="2026-07-05")

    assert next_charge_on(sub, "2026-07-26") == "2026-07-26"


def test_frequencies_are_normalised_to_a_comparable_month() -> None:
    """Otherwise a gym paid weekly looks cheaper than a magazine paid monthly."""
    weekly = subscription(frequency="weekly", amount=10_000)
    monthly = subscription(frequency="monthly", amount=30_900)
    yearly = subscription(frequency="yearly", amount=120_000)

    assert monthly_equivalent(weekly) == 43_333  # 10.000 * 52 / 12
    assert monthly_equivalent(monthly) == 30_900
    assert monthly_equivalent(yearly) == 10_000

    assert yearly_equivalent(weekly) == 520_000
    assert yearly_equivalent(monthly) == 370_800
    assert yearly_equivalent(yearly) == 120_000
