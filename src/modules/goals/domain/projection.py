"""Where a goal lands at the user's real contribution pace — derived, never stored.

The prototype persisted `projectionMonth: "octubre"`, a display string that was wrong
the month after it was written (the «21 may» class of bug). These functions take the
raw facts — what is saved, when the first contribution happened, today — and answer
fresh on every read.

The agent's projection (Fase 4, from the real savings rate) will replace this from
above; until then the arithmetic is honest and testable.
"""

from datetime import date

# A month of pace, in days. Two contributions three days apart must not promise the
# month's rhythm — the divisor never drops under a month.
DAYS_PER_MONTH = 30


def monthly_pace(*, saved: int, first_in_on: str, today: str) -> int:
    """What the user sets aside per month, from the whole history.

    The window runs from the first contribution to today, floored at one month: a
    $900.000 first week would otherwise "prove" a $3.6M month.
    """
    days = (date.fromisoformat(today) - date.fromisoformat(first_in_on)).days
    return saved * DAYS_PER_MONTH // max(DAYS_PER_MONTH, days)


def projected_on(*, saved: int, target: int, first_in_on: str | None, today: str) -> str | None:
    """`YYYY-MM` the goal is reached at the current pace.

    `None` when there is nothing to project from (no contributions, no pace) — better
    silent than alarming — and when the goal is already reached: the future already
    happened.
    """
    if saved >= target:
        return None
    if first_in_on is None or saved <= 0:
        return None
    pace = monthly_pace(saved=saved, first_in_on=first_in_on, today=today)
    if pace <= 0:
        return None

    remaining = target - saved
    # Ceiling division: a month you land partway through still has to pass.
    months = -(-remaining // pace)
    anchor = date.fromisoformat(today)
    total = anchor.year * 12 + (anchor.month - 1) + months
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def needed_per_month(*, saved: int, target: int, target_date: str | None, today: str) -> int | None:
    """What each remaining month needs for the goal to land on its date.

    `None` without a date, once the goal is reached, or when the date already passed —
    a required pace for a deadline behind you is not advice, it is a reproach.
    """
    if target_date is None or saved >= target:
        return None
    days = (date.fromisoformat(target_date) - date.fromisoformat(today)).days
    if days <= 0:
        return None
    months = max(1, days // DAYS_PER_MONTH)
    return -(-(target - saved) // months)
