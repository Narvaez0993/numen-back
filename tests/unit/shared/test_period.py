"""The calendar two modules share.

The trap this file guards is in the field names: `days_elapsed` and `days_left` **both
include today**, so they do not add up to the month. Whoever reads only one of them is
fine; whoever adds them is off by a day.
"""

from datetime import date

from src.shared.domain.period import MonthPeriod


def test_both_day_counts_include_today_so_they_overlap_by_one() -> None:
    july_26 = MonthPeriod.containing(date(2026, 7, 26))

    assert july_26.total_days == 31
    assert july_26.days_elapsed == 26
    assert july_26.days_left == 6  # 26..31, today included
    assert july_26.days_elapsed + july_26.days_left == july_26.total_days + 1


def test_the_month_is_named_and_bounded_by_the_day_it_contains() -> None:
    february = MonthPeriod.containing(date(2028, 2, 3))

    assert february.key == "2028-02"
    assert february.first_day == "2028-02-01"
    assert february.last_day == "2028-02-29"  # leap year, from the calendar
    assert february.total_days == 29


def test_the_last_day_of_the_month_still_has_one_day_left() -> None:
    """`days_left` is never zero while the month is open — it is the divisor of the
    daily ceiling, and on the 31st the whole remainder is for today."""
    assert MonthPeriod.containing(date(2026, 7, 31)).days_left == 1


def test_the_comparable_span_is_cut_at_the_same_day() -> None:
    july_26 = MonthPeriod.containing(date(2026, 7, 26))

    assert july_26.same_span_last_month() == ("2026-06-01", "2026-06-26")


def test_the_comparable_span_is_clamped_when_last_month_was_shorter() -> None:
    assert MonthPeriod.containing(date(2026, 3, 31)).same_span_last_month() == (
        "2026-02-01",
        "2026-02-28",
    )


def test_january_compares_against_december_of_the_year_before() -> None:
    assert MonthPeriod.containing(date(2026, 1, 15)).same_span_last_month() == (
        "2025-12-01",
        "2025-12-15",
    )
