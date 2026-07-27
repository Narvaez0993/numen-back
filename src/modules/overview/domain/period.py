from calendar import monthrange
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MonthPeriod:
    """The month a day belongs to, plus how much of it is left and gone.

    Derived from the day the **client** says it is, not from the server's UTC date: a
    user in UTC+13 opening the app in the morning is already on a different day than
    the server, and every figure about "this month so far" would be off.
    """

    key: str
    """`YYYY-MM` — how the UI names the month."""
    first_day: str
    last_day: str
    total_days: int
    """Days the month has. `days_elapsed + days_left` is **not** it: both include
    today, so adding them counts today twice — which is exactly how a projection ended
    up estimating 32 days of spending in a 31-day month."""
    days_left: int
    """Including today, so it is never zero while the month is open. This is the
    figure a label wants ("6 days left"), not the one a projection wants."""
    days_elapsed: int
    """Including today — the denominator of the spending pace."""

    @classmethod
    def containing(cls, today: date) -> "MonthPeriod":
        _, total_days = monthrange(today.year, today.month)
        return cls(
            key=f"{today.year:04d}-{today.month:02d}",
            first_day=today.replace(day=1).isoformat(),
            last_day=today.replace(day=total_days).isoformat(),
            total_days=total_days,
            days_left=total_days - today.day + 1,
            days_elapsed=today.day,
        )

    def same_span_last_month(self) -> tuple[str, str]:
        """Last month, cut at the same day — the only fair comparison mid-month.

        July 1-26 against June 1-26, never against the whole of June: a month in
        progress compared to a finished one would always look better, and a trend that
        flatters you is worse than no trend. Clamped when the previous month is shorter
        (the 31st becomes the 28th).
        """
        first = date.fromisoformat(self.first_day)
        year, month = (first.year, first.month - 1) if first.month > 1 else (first.year - 1, 12)
        _, total_days = monthrange(year, month)
        return (
            date(year, month, 1).isoformat(),
            date(year, month, min(self.days_elapsed, total_days)).isoformat(),
        )
