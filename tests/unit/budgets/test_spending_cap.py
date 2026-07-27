"""The daily ceiling.

Two properties are pinned here, and one of them is a limit worth stating out loud:

1. **It falls as the user spends** — every peso spent lowers what the rest of the days
   get. That is the direction that matters.
2. **It rises as days pass with money unspent**, exactly like the allowance it replaced
   did. What changed is whose number is being divided: a limit the user chose, never the
   income the app found. It is bounded by the cap, and that bound is asserted below.

The divisor is `days_left`, **today included** — the same input that was *wrong* for the
projection, where adding it to `days_elapsed` counted the month as 32 days. Right here,
wrong there, because the questions are different: this one has to cover today.
"""

from src.modules.budgets.domain.spending_cap import progress

TARGET = 3_000_000
TOTAL_DAYS = 31


def july(*, spent: int, day: int):
    """The cap as it stands on a given day of July."""
    return progress(
        target=TARGET,
        spent=spent,
        days_left=TOTAL_DAYS - day + 1,
        days_elapsed=day,
        total_days=TOTAL_DAYS,
    )


def test_the_ceiling_falls_as_the_user_spends() -> None:
    """The property the allowance violated: what is left, over fewer days, still buys
    less per day — never more."""
    before = july(spent=1_000_000, day=15)
    after = july(spent=1_400_000, day=15)

    assert before.per_day is not None
    assert after.per_day is not None
    assert after.per_day < before.per_day


def test_holding_back_does_raise_it_and_the_cap_is_the_bound() -> None:
    """The honest limitation: a day passing with nothing spent leaves the same remainder
    over one less day, so the figure goes up.

    It is acceptable because of what is being divided — a ceiling the user set, which the
    ceiling can never exceed. This asserts that bound: whatever the day, spending `per_day`
    for every remaining day cannot break the cap.
    """
    day_15 = july(spent=1_000_000, day=15)
    day_16 = july(spent=1_000_000, day=16)

    assert day_15.per_day is not None
    assert day_16.per_day is not None
    assert day_16.per_day > day_15.per_day

    for day in range(1, TOTAL_DAYS + 1):
        cap = july(spent=1_000_000, day=day)
        assert cap.per_day is not None
        assert 1_000_000 + cap.per_day * (TOTAL_DAYS - day + 1) <= TARGET


def test_on_the_last_day_the_whole_remainder_is_for_today() -> None:
    """`days_left` includes today, so it is 1 on the 31st — dividing by 0 would be the
    off-by-one going the other way."""
    cap = july(spent=2_800_000, day=31)

    assert cap.per_day == 200_000
    assert cap.remaining == 200_000


def test_going_over_is_reported_not_clamped() -> None:
    """A `max(0, ...)` here would tell someone $300.000 past their cap that they have
    $0 left, which is a different and friendlier lie."""
    cap = july(spent=3_300_000, day=20)

    assert cap.remaining == -300_000
    assert cap.per_day is None
    assert cap.used > 1


def test_used_is_not_capped_so_the_client_can_draw_the_overflow() -> None:
    assert july(spent=4_200_000, day=20).used == 1.4


def test_a_spent_cap_leaves_nothing_to_divide() -> None:
    cap = july(spent=TARGET, day=20)

    assert cap.remaining == 0
    assert cap.per_day is None


def test_the_projection_says_whether_the_month_closes_over_the_cap() -> None:
    # 2.600.000 in 20 days is 130.000/day, which lands at about 4.03M on a 31-day month.
    cap = july(spent=2_600_000, day=20)

    assert cap.projected == 4_030_000
    assert cap.over == 1_030_000


def test_no_overrun_is_null_and_not_a_zero() -> None:
    """The client alarms about a number; a 0 would draw the amber warning over nothing."""
    cap = july(spent=1_000_000, day=20)

    assert cap.projected is not None
    assert cap.projected < TARGET
    assert cap.over is None


def test_the_first_days_of_the_month_project_nothing_but_still_have_a_ceiling() -> None:
    """One restaurant bill on the 2nd would forecast a month of them — but the ceiling
    is not a forecast, and it is available from day one."""
    cap = july(spent=200_000, day=2)

    assert cap.projected is None
    assert cap.over is None
    assert cap.per_day == (TARGET - 200_000) // 30
