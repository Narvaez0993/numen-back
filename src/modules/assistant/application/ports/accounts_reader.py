"""Outbound port: accounts and balances, as facts for the agent's tools.

Views carry what the model needs to reason and stage drafts (ids, names, kinds,
balances) — not what a screen needs (icons, colors, ordering).
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class AccountView:
    id: str
    name: str
    kind: str
    balance: int


@dataclass(frozen=True)
class CreditCardView:
    id: str
    name: str
    debt: int
    limit: int | None


@dataclass(frozen=True)
class AccountsView:
    currency: str
    net_balance: int
    debit_total: int
    cash_total: int
    card_debt_total: int
    accounts: tuple[AccountView, ...]
    credit_cards: tuple[CreditCardView, ...]


class AccountsReader(Protocol):
    async def overview(self, user_id: UUID, currency: str) -> AccountsView: ...
