from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.modules.movements.domain.entities.movement import SourceRef, SourceType


@dataclass(frozen=True)
class SourceSnapshot:
    """What movements needs to know about a source to validate against it."""

    ref: SourceRef
    type: SourceType
    currency: str


class SourceLedger(Protocol):
    """Outbound port: reads sources and applies a movement's money effect.

    This is the seam that keeps `movements` from importing `accounts`: the module
    states *what* it needs (does this source exist, move it by this delta) and an
    adapter translates that into account balances and card debts.

    `apply_delta` must be a single atomic increment, not a read-modify-write: a
    movement only ever moves the current balance, never the reconciliation anchor
    (`initial_balance` / `initial_debt`).
    """

    async def find(self, user_id: UUID, ref: SourceRef) -> SourceSnapshot | None: ...

    async def apply_delta(self, user_id: UUID, ref: SourceRef, delta: int) -> None: ...
