from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class PocketFunds:
    """What one pocket holds, summed from the transfers that filled it."""

    goal_id: str
    saved: int
    first_in_on: str | None


class FundsReader(Protocol):
    """Outbound port: pocket money, read from wherever movements live.

    `goals` declares the shape it needs instead of importing the movements module —
    the same anti-corruption seam every other module uses. The pocket has no stored
    balance on purpose: its money IS those transfers, so it cannot drift.
    """

    async def funds(self, user_id: UUID) -> dict[str, PocketFunds]: ...
