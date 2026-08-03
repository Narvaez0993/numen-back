"""Holgura — the domain's answer to "does a treat actually fit?".

«Date un gusto» only ships when the math says so: what came in this month,
minus what already left, minus the charges still queued to leave, minus the
pace a goal needs. Settled charges must NOT be passed in — they already live
inside `expense`, and counting them twice would kill every treat unfairly.
"""


def monthly_slack(
    income: int,
    expense: int,
    pending_charges: int,
    goal_needed: int | None,
) -> int:
    """Can go negative — the caller reads that as "no room at all"."""
    return income - expense - pending_charges - (goal_needed or 0)
