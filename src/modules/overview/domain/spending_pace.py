"""How fast the month is going — the figure that replaced the daily allowance.

The projection itself lives in `shared/domain/month_projection.py`, because `budgets`
has to land on the same number when it compares the close against a cap. What stays
here is what only Home says: the daily average and the trend against last month.
"""

from dataclasses import dataclass

from src.shared.domain.month_projection import project


@dataclass(frozen=True)
class SpendingPace:
    """What the month is costing per day, and where it lands at this rate."""

    daily_average: int
    projected: int


def compute(*, spent: int, days_elapsed: int, total_days: int) -> SpendingPace | None:
    """`None` while the month is too young to project from — see `project`."""
    projected = project(spent=spent, days_elapsed=days_elapsed, total_days=total_days)
    if projected is None:
        return None

    return SpendingPace(daily_average=spent // days_elapsed, projected=projected)


def change(current: int, previous: int) -> float | None:
    """Signed share of change against the same stretch of last month.

    `None` when there is nothing to compare against — a first month has no trend, and
    a 0 there would read as "you spent the same", which is a different claim.
    """
    if previous <= 0:
        return None
    return (current - previous) / previous
