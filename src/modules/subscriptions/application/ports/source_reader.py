from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.modules.subscriptions.domain.entities.subscription import SourceRef


@dataclass(frozen=True)
class SourceSnapshot:
    """What subscriptions needs to know about a source to validate against it."""

    ref: SourceRef
    currency: str


class SourceReader(Protocol):
    """Outbound port: does this account or card exist, and in what currency?

    The read-only half of movements' `SourceLedger`: a subscription **never moves
    money**. When a charge is settled, the movement does it — and it goes through
    the movements module, which owns that rule.
    """

    async def find(self, user_id: UUID, ref: SourceRef) -> SourceSnapshot | None: ...
