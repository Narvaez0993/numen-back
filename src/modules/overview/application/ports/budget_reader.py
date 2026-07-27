from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class GlobalCapView:
    """The month's ceiling as Home needs it — already measured, not raw.

    Home could compute this from the target and the figures it already holds, and that
    is exactly what it must not do: the daily ceiling would then exist in two places and
    the two screens would eventually show different numbers for the same month. The
    module that owns the cap owns its arithmetic.
    """

    target: int
    spent: int
    remaining: int
    used: float
    per_day: int | None
    projected: int | None
    over: int | None


class BudgetReader(Protocol):
    """Outbound port: the global cap for a day, or `None` if the user set none."""

    async def global_cap(self, user_id: UUID, today: str) -> GlobalCapView | None: ...
