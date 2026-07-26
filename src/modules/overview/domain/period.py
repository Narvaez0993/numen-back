from calendar import monthrange
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MonthPeriod:
    """The month a day belongs to, plus how much of it is left.

    Derived from the day the **client** says it is, not from the server's UTC
    date: a user in UTC+13 opening the app in the morning is already on a
    different day than the server, and "how much can I spend today" would be off.
    """

    key: str
    """`YYYY-MM` — how the UI names the month."""
    first_day: str
    last_day: str
    days_left: int
    """Including today, so it is never zero while the month is open."""

    @classmethod
    def containing(cls, today: date) -> "MonthPeriod":
        _, total_days = monthrange(today.year, today.month)
        return cls(
            key=f"{today.year:04d}-{today.month:02d}",
            first_day=today.replace(day=1).isoformat(),
            last_day=today.replace(day=total_days).isoformat(),
            days_left=total_days - today.day + 1,
        )
