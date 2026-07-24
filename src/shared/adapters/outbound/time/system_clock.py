from datetime import UTC, datetime


class SystemClock:
    """`Clock` implementation returning the real wall-clock time in UTC."""

    def now(self) -> datetime:
        return datetime.now(UTC)
