from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class BalanceSnapshot:
    """What the user is worth right now, as the Accounts screen computes it."""

    net_balance: int
    accounts_count: int
    credit_cards_count: int


class BalanceReader(Protocol):
    """Outbound port: the net position, read from wherever sources live.

    `overview` never imports `accounts`: it says what it needs and an adapter in
    its own outermost layer translates. Same anti-corruption seam `movements` uses
    with `SourceLedger`.
    """

    async def read(self, user_id: UUID, currency: str) -> BalanceSnapshot: ...
