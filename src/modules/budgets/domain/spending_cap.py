"""How a month is going against a cap the user set.

This is where the daily figure comes back, and the difference from the one that was
deleted is the whole point:

- **the allowance** was `(income - spent) / days_left` — the app deciding what the user
  could afford, and it *rose* every day they held back;
- **the ceiling** is `(target - spent) / days_left` — the user's own number spread over
  the days it still has to cover, and it can only fall when they spend.

⚠️ Note that the ceiling divides by `days_left` **including today**, which is exactly the
input that broke the projection in `shared/domain/month_projection.py`. It is right here
and wrong there, and the reason is the question each one answers:

- the projection asks *"where does the month land"* -> the month has `total_days`, and
  since `days_elapsed` already counts today, adding `days_left` counts it twice (a
  31-day month came out as 32);
- the ceiling asks *"how much for today and what is left"* -> today is one of the days
  that still needs covering, so it belongs in the divisor. On the 31st, `days_left` is
  1 and the whole remainder is for today, which is correct.

Do not "fix" one to look like the other.
"""

from dataclasses import dataclass

from src.shared.domain.month_projection import project


@dataclass(frozen=True)
class CapProgress:
    """A cap and the month measured against it."""

    target: int
    spent: int
    remaining: int
    """`target - spent`. **Negative when the user went over**, and it is reported that
    way: a `max(0, ...)` here would show $0 left to someone already $300.000 past their
    cap, which is the moment they most need the truth."""
    used: float
    """`spent / target`, uncapped: `1.4` means 140% and the client draws the overflow."""
    per_day: int | None
    """The ceiling for each remaining day. `None` once the cap is spent — there is
    nothing left to divide, and a negative "per day" is not a thing."""
    projected: int | None
    """Where the month closes at the current rate. `None` in the first days, when a
    single bill would forecast a whole month of them."""
    over: int | None
    """How much past the cap the month would close. `None` when it closes inside it —
    the client shows an alert for a number, not for a zero."""


def progress(
    *,
    target: int,
    spent: int,
    days_left: int,
    days_elapsed: int,
    total_days: int,
) -> CapProgress:
    """`days_left` includes today and is therefore never zero while the month is open
    (see `MonthPeriod`); `target` is positive by the entity's invariant."""
    remaining = target - spent
    projected = project(spent=spent, days_elapsed=days_elapsed, total_days=total_days)

    return CapProgress(
        target=target,
        spent=spent,
        remaining=remaining,
        used=spent / target,
        per_day=remaining // days_left if remaining > 0 else None,
        projected=projected,
        over=projected - target if projected is not None and projected > target else None,
    )
