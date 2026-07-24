from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Outbound port: the current instant, always timezone-aware in UTC.

    Injected wherever time matters so expirations and cooldowns stay
    deterministic under test.
    """

    def now(self) -> datetime: ...
