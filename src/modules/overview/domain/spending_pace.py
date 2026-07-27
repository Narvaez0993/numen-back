"""How fast the month is going — the figure that replaced the daily allowance.

The hero used to divide `(income - spent)` by the days left and call it "available
today". That number had the incentive backwards: spending nothing today made
**tomorrow's figure bigger**, because the same money was split across fewer days. On
the 31st it granted the whole remaining income for a single day.

The pace never does that. It looks at what has already happened — how much per day
you are actually spending — and projects the rest of the month from it. Underspending
today can only lower tomorrow's projection.
"""

from dataclasses import dataclass

# Under this, a projection is noise: one restaurant bill on the 2nd would forecast a
# month of eating out. Better to say nothing than to alarm someone over a Tuesday.
MIN_DAYS_FOR_PROJECTION = 3


@dataclass(frozen=True)
class SpendingPace:
    """What the month is costing per day, and where it lands at this rate."""

    daily_average: int
    projected: int


def compute(*, spent: int, days_elapsed: int, days_left: int) -> SpendingPace | None:
    """`None` while the month is too young to project from.

    Only the **remaining** days are projected: what was already spent is a fact and is
    carried as-is, so the estimate can never contradict the ledger.
    """
    if days_elapsed < MIN_DAYS_FOR_PROJECTION or spent <= 0:
        return None

    return SpendingPace(
        daily_average=spent // days_elapsed,
        projected=spent + spent * days_left // days_elapsed,
    )


def change(current: int, previous: int) -> float | None:
    """Signed share of change against the same stretch of last month.

    `None` when there is nothing to compare against — a first month has no trend, and
    a 0 there would read as "you spent the same", which is a different claim.
    """
    if previous <= 0:
        return None
    return (current - previous) / previous
