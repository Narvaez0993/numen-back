"""Outbound port: the only thing persisted about rule insights.

Insights are recomputed on every read; a dismissal is the user saying "stop
showing me this one" — stored by its deterministic key and forgotten by TTL
long after the period in the key has passed.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID


class InsightDismissals(Protocol):
    async def dismiss(self, user_id: UUID, key: str, at: datetime) -> None:
        """Idempotent upsert."""
        ...

    async def dismissed_among(self, user_id: UUID, keys: Sequence[str]) -> frozenset[str]:
        """Which of `keys` this user already dismissed — one query."""
        ...
