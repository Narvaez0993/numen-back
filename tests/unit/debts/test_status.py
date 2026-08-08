"""What is left and the state it is in — all derived, with `today` as an input.

The prototype persisted a `balance` and displayed due dates as strings ("21 may"), and
both went stale. These are the functions that replaced them, so the properties they pin
are the ones that rot silently: paid beats the calendar, overdue needs money owed, and
`remaining` is always the amount minus what came back.

What came back is not a field of the debt any more — it is the transfers that carried
it. `repaid` arrives as a plain number here so the domain stays pure arithmetic; which
transfers count as repayments is `settlement.py`'s job, tested next door.
"""

from src.modules.debts.domain.status import remaining, status

from .fakes import TODAY, debt, new_user_id

YESTERDAY = "2026-07-26"
TOMORROW = "2026-07-28"


def test_a_fresh_debt_is_pending() -> None:
    assert status(debt(user_id=new_user_id()), 0, TODAY) == "pending"


def test_payments_make_it_partial_and_remaining_is_the_arithmetic() -> None:
    d = debt(user_id=new_user_id(), amount=120_000)

    assert status(d, 45_000, TODAY) == "partial"
    assert remaining(d, 45_000) == 75_000


def test_the_exact_payment_settles_it() -> None:
    d = debt(user_id=new_user_id(), amount=120_000)

    assert status(d, 120_000, TODAY) == "paid"
    assert remaining(d, 120_000) == 0


def test_a_due_date_in_the_past_with_money_owed_is_overdue() -> None:
    d = debt(user_id=new_user_id(), due_on=YESTERDAY)

    assert status(d, 1_000, TODAY) == "overdue"


def test_paid_wins_over_the_calendar() -> None:
    """A settled debt cannot be overdue, however late it was paid."""
    d = debt(user_id=new_user_id(), amount=50_000, due_on=YESTERDAY)

    assert status(d, 50_000, TODAY) == "paid"


def test_due_today_is_not_overdue_yet() -> None:
    assert status(debt(user_id=new_user_id(), due_on=TODAY), 0, TODAY) == "pending"


def test_due_tomorrow_is_just_pending() -> None:
    assert status(debt(user_id=new_user_id(), due_on=TOMORROW), 0, TODAY) == "pending"


def test_no_due_date_never_goes_overdue() -> None:
    assert status(debt(user_id=new_user_id()), 1_000, "2030-01-01") == "partial"


def test_giving_up_beats_every_other_state() -> None:
    """Written off and paid are two different words for the same zero: one was
    collected, the other was lost. A screen that called them both PAGADO would tell
    the user a friend paid them back when nobody did."""
    given_up = debt(user_id=new_user_id(), amount=120_000, written_off_on=YESTERDAY)

    assert status(given_up, 0, TODAY) == "written_off"
    assert remaining(given_up, 0) == 0


def test_a_written_off_debt_stops_being_owed_even_when_it_was_overdue() -> None:
    """`remaining` going to zero is what takes it out of every total in the app,
    without a single caller having to remember the case."""
    given_up = debt(user_id=new_user_id(), amount=90_000, due_on=YESTERDAY, written_off_on=TODAY)

    assert remaining(given_up, 30_000) == 0
    assert status(given_up, 30_000, TODAY) == "written_off"


def test_a_ledger_never_reports_owing_less_than_nothing() -> None:
    """`remaining` is clamped. Repayments are derived from movements now, so a stray
    transfer could in principle outrun the principal — better a floor than a debt
    that claims the person is owed money back."""
    d = debt(user_id=new_user_id(), amount=50_000)

    assert remaining(d, 80_000) == 0
    assert status(d, 80_000, TODAY) == "paid"
