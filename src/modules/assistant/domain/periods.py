"""Period arithmetic for the proactive jobs — the ONLY place it lives.

Months are `YYYY-MM`; weeks are ISO (`2026-W31`, Monday through Sunday). The
weekly job runs on Mondays and reviews the week just finished: the ISO week
containing `today - 7 days`.
"""

from datetime import date, timedelta


def previous_month(today: str) -> str:
    day = date.fromisoformat(today)
    year, month = (day.year, day.month - 1) if day.month > 1 else (day.year - 1, 12)
    return f"{year:04d}-{month:02d}"


def month_bounds(period: str) -> tuple[str, str]:
    first = date.fromisoformat(f"{period}-01")
    if first.month == 12:
        next_first = first.replace(year=first.year + 1, month=1)
    else:
        next_first = first.replace(month=first.month + 1)
    return first.isoformat(), (next_first - timedelta(days=1)).isoformat()


def week_label(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year:04d}-W{week:02d}"


def previous_iso_week(today: str) -> str:
    """The full ISO week that just ended — the one containing `today - 7d`."""
    return week_label(date.fromisoformat(today) - timedelta(days=7))


def iso_week_bounds(period: str) -> tuple[str, str]:
    year, week = int(period[:4]), int(period.split("W")[1])
    monday = date.fromisocalendar(year, week, 1)
    return monday.isoformat(), (monday + timedelta(days=6)).isoformat()


def previous_iso_week_label(period: str) -> str:
    monday, _ = iso_week_bounds(period)
    return week_label(date.fromisoformat(monday) - timedelta(days=7))


def round_to_nice(amount: int) -> int:
    """Up to a round figure a human would set as a cap ($287.450 → $290.000)."""
    if amount <= 0:
        return 0
    digits = len(str(amount))
    step: int = 10 ** max(0, digits - 2)
    return ((amount + step - 1) // step) * step


def round_to_nice_down(amount: int) -> int:
    """Down — a treat suggestion never overshoots what actually fits."""
    if amount <= 0:
        return 0
    digits = len(str(amount))
    step: int = 10 ** max(0, digits - 2)
    return (amount // step) * step
