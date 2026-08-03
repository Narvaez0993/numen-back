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


@dataclass(frozen=True)
class CategoryCapView:
    """A category's cap, measured by the module that owns it.

    Only the two figures the Home row shows: the limit, and how much of it is gone. No
    daily ceiling and no projection — a category is not where this app spreads a number
    over the days, and a figure that nothing renders is a figure that goes stale unseen.

    `used` arrives measured for the same reason as the ceiling above: dividing here would
    put `spent / target` in two modules, and the Presupuestos screen would be the only one
    that noticed if that ever stopped being the definition.
    """

    target: int
    used: float


class BudgetReader(Protocol):
    """Outbound port: the caps Home puts its own figures against."""

    async def global_cap(self, user_id: UUID, today: str) -> GlobalCapView | None:
        """The month's ceiling for a day, or `None` if the user set none."""
        ...

    async def category_caps(self, user_id: UUID, today: str) -> dict[str, CategoryCapView]:
        """The watched categories, by id. Empty for someone who watches none — Home then
        weighs its categories against the month's spending instead."""
        ...
