"""When a subscription charges — the whole cadence rule, as pure functions.

Every date is derived from `first_charge_on` + `frequency`; nothing about the
schedule is stored. That is what keeps "next charge" honest: a persisted
`next_charge_at` would need a writer to advance it and would be wrong the moment
that writer failed. Same reasoning as `occurred_on` being a date and the day
labels being derived at render time.

Monthly is the interesting case: an anchor on the 31st charges on the 30th, the
28th or the 29th depending on the month. It **clamps, never rolls over** — a
January 31st subscription is a February 28th one, not a March 3rd one.
"""

import calendar
from datetime import date, timedelta

from src.modules.subscriptions.domain.entities.subscription import Frequency, Subscription

# How long the user has to confirm a charge before it is registered for them.
CONFIRMATION_WINDOW_HOURS = 3

# How far back the opener looks. Without it, a worker that was down for an hour
# would silently skip a charge forever; with more, a long outage would flood the
# user with old charges. Two days is enough to survive a restart and short enough
# that nothing surprising appears.
CATCH_UP_DAYS = 2

# Weeks and months do not divide evenly; these are the conversions used to state a
# monthly total. 52/12 (not 4) so a weekly charge is not understated by 8 percent.
_WEEKS_PER_YEAR = 52
_MONTHS_PER_YEAR = 12


def _clamped(year: int, month: int, day: int) -> date:
    """`day` capped to the length of that month (31 → 30 → 29 → 28)."""
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def _shift_months(anchor: date, months: int) -> date:
    total = anchor.month - 1 + months
    return _clamped(anchor.year + total // 12, total % 12 + 1, anchor.day)


def occurrences(
    subscription: Subscription, date_from: str, date_to: str, *, include_paused: bool = False
) -> list[str]:
    """Every charge date in `[date_from, date_to]`, oldest first.

    Dates before the anchor are never produced: a subscription created today does
    not owe anything for last month.
    """
    if not subscription.active and not include_paused:
        return []

    anchor = date.fromisoformat(subscription.first_charge_on)
    start = max(date.fromisoformat(date_from), anchor)
    end = date.fromisoformat(date_to)
    if start > end:
        return []

    dates: list[str] = []
    for current in _walk(anchor, subscription.frequency, until=end):
        if current >= start:
            dates.append(current.isoformat())
    return dates


def _walk(anchor: date, frequency: Frequency, *, until: date) -> list[date]:
    """Charge dates from the anchor up to `until`, inclusive."""
    if frequency == "weekly":
        step = timedelta(days=7)
        dates: list[date] = []
        current = anchor
        while current <= until:
            dates.append(current)
            current += step
        return dates

    months = 1 if frequency == "monthly" else _MONTHS_PER_YEAR
    dates = []
    index = 0
    while True:
        # Always shifted from the anchor, never from the previous result: chaining
        # a clamped date would drag the 31st down to the 28th forever.
        current = _shift_months(anchor, months * index)
        if current > until:
            return dates
        dates.append(current)
        index += 1


def next_charge_on(subscription: Subscription, today: str) -> str | None:
    """The first charge falling on or after `today`. `None` if it is paused."""
    if not subscription.active:
        return None

    anchor = date.fromisoformat(subscription.first_charge_on)
    reference = date.fromisoformat(today)
    if anchor >= reference:
        return anchor.isoformat()

    if subscription.frequency == "weekly":
        elapsed = (reference - anchor).days
        return (anchor + timedelta(days=((elapsed + 6) // 7) * 7)).isoformat()

    months = 1 if subscription.frequency == "monthly" else _MONTHS_PER_YEAR
    index = 0
    while True:
        index += 1
        candidate = _shift_months(anchor, months * index)
        if candidate >= reference:
            return candidate.isoformat()


def monthly_equivalent(subscription: Subscription) -> int:
    """What this subscription costs per month, to state a comparable total.

    Weekly and yearly are normalised, so "monthly total" means the same thing for
    a gym paid weekly and a domain paid once a year.
    """
    if subscription.frequency == "monthly":
        return subscription.amount
    if subscription.frequency == "weekly":
        return subscription.amount * _WEEKS_PER_YEAR // _MONTHS_PER_YEAR
    return subscription.amount // _MONTHS_PER_YEAR


def yearly_equivalent(subscription: Subscription) -> int:
    if subscription.frequency == "monthly":
        return subscription.amount * _MONTHS_PER_YEAR
    if subscription.frequency == "weekly":
        return subscription.amount * _WEEKS_PER_YEAR
    return subscription.amount
