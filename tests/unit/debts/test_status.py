"""What is left and the state it is in — all derived, with `today` as an input.

The prototype persisted a `balance` and displayed due dates as strings ("21 may"), and
both went stale. These are the functions that replaced them, so the properties they pin
are the ones that rot silently: paid beats the calendar, overdue needs money owed, and
`remaining` is always the amount minus the payments.
"""

from src.modules.debts.domain.status import paid_total, remaining, status

from .fakes import TODAY, debt, new_user_id, payment

YESTERDAY = "2026-07-26"
TOMORROW = "2026-07-28"


def test_a_fresh_debt_is_pending() -> None:
    assert status(debt(user_id=new_user_id()), TODAY) == "pending"


def test_payments_make_it_partial_and_remaining_is_the_arithmetic() -> None:
    d = debt(user_id=new_user_id(), amount=120_000, payments=(payment(amount=45_000),))

    assert status(d, TODAY) == "partial"
    assert paid_total(d) == 45_000
    assert remaining(d) == 75_000


def test_the_exact_payment_settles_it() -> None:
    d = debt(
        user_id=new_user_id(),
        amount=120_000,
        payments=(payment(amount=100_000), payment(amount=20_000)),
    )

    assert status(d, TODAY) == "paid"
    assert remaining(d) == 0


def test_a_due_date_in_the_past_with_money_owed_is_overdue() -> None:
    d = debt(user_id=new_user_id(), due_on=YESTERDAY, payments=(payment(amount=1_000),))

    assert status(d, TODAY) == "overdue"


def test_paid_wins_over_the_calendar() -> None:
    """A settled debt cannot be overdue, however late it was paid."""
    d = debt(
        user_id=new_user_id(), amount=50_000, due_on=YESTERDAY, payments=(payment(amount=50_000),)
    )

    assert status(d, TODAY) == "paid"


def test_due_today_is_not_overdue_yet() -> None:
    assert status(debt(user_id=new_user_id(), due_on=TODAY), TODAY) == "pending"


def test_due_tomorrow_is_just_pending() -> None:
    assert status(debt(user_id=new_user_id(), due_on=TOMORROW), TODAY) == "pending"


def test_no_due_date_never_goes_overdue() -> None:
    d = debt(user_id=new_user_id(), payments=(payment(amount=1_000),))

    assert status(d, "2030-01-01") == "partial"
