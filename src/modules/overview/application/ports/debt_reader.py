from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class DebtTotalsView:
    """Money between the user and people, already summed by the module that owns it.

    `i_owe` is what completes the debt rung: cards were the only debt Home knew about.
    `owed_to_me` is the other direction — an asset, shown as a line, never added to
    what the user owes.
    """

    i_owe: int
    owed_to_me: int
    open_count: int


class DebtReader(Protocol):
    """Outbound port: live personal-debt totals."""

    async def totals(self, user_id: UUID) -> DebtTotalsView: ...
