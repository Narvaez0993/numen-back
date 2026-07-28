"""Outbound port: the two flat counters, keyed by `(user, YYYY-MM)`.

The month rollover is the key itself — a new period upserts a fresh row at
zero, so there is no reset job to run (and no reset job to fail on the 1st).
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class UsageView:
    registrations_used: int
    messages_used: int


class UsageCounters(Protocol):
    async def month_usage(self, user_id: UUID, period: str) -> UsageView: ...

    async def consume(
        self, user_id: UUID, period: str, *, registrations: int, messages: int
    ) -> None:
        """Atomic `$inc` upsert; called inside the turn's commit."""
        ...
