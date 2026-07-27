from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class BalanceSnapshot:
    """What the user is worth right now, as the Accounts screen computes it.

    `card_debt` and `card_limit` are here because they are the only debt figure that
    exists today: a card's debt is real, the cash-basis moves it, and it is what Home
    leads with for someone whose objective is getting out of debt. Person-to-person
    debt joins them when the `debts` module lands.
    """

    net_balance: int
    accounts_count: int
    credit_cards_count: int
    card_debt: int
    card_limit: int


class BalanceReader(Protocol):
    """Outbound port: the net position, read from wherever sources live.

    `overview` never imports `accounts`: it says what it needs and an adapter in
    its own outermost layer translates. Same anti-corruption seam `movements` uses
    with `SourceLedger`.
    """

    async def read(self, user_id: UUID, currency: str) -> BalanceSnapshot: ...
