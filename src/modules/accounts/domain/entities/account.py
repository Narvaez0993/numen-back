from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

AccountKind = Literal["debit", "cash"]

ALLOWED_KINDS: frozenset[str] = frozenset({"debit", "cash"})
ALLOWED_COLORS: frozenset[str] = frozenset({"mint", "coral", "purple", "amber", "pink", "neutral"})
MAX_NAME_LENGTH = 40
MAX_SUB_LENGTH = 40
# Sanity bound for money in minor units (~10 trillion major units).
MAX_AMOUNT = 10**15

DEFAULT_ICONS: dict[str, str] = {"debit": "building-bank", "cash": "cash"}
DEFAULT_COLOR = "mint"


def default_icon(kind: AccountKind) -> str:
    return DEFAULT_ICONS[kind]


@dataclass(frozen=True)
class Account:
    """Where money sits: a bank/debit account or cash.

    `balance` is the current balance in the minor unit of `currency` (cents for
    USD, pesos for COP) and `initial_balance` is the anchor it started from, so
    that `balance == initial_balance + Σ movements` always holds. A manual
    balance edit shifts `initial_balance` by the same delta instead of inventing
    a movement — that keeps the ledger reconcilable once `movements` lands,
    while reads stay a single query (no aggregation over history).
    """

    id: str
    user_id: UUID
    kind: AccountKind
    name: str
    sub: str
    icon: str
    color: str
    currency: str
    balance: int
    initial_balance: int
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        kind: AccountKind,
        name: str,
        sub: str,
        icon: str,
        color: str,
        currency: str,
        balance: int,
        created_at: datetime,
    ) -> "Account":
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            kind=kind,
            name=name,
            sub=sub,
            icon=icon,
            color=color,
            currency=currency,
            balance=balance,
            initial_balance=balance,
            created_at=created_at,
        )

    def with_updates(
        self,
        *,
        name: str | None = None,
        sub: str | None = None,
        icon: str | None = None,
        color: str | None = None,
        balance: int | None = None,
    ) -> "Account":
        new_balance = self.balance if balance is None else balance
        return replace(
            self,
            name=self.name if name is None else name,
            sub=self.sub if sub is None else sub,
            icon=self.icon if icon is None else icon,
            color=self.color if color is None else color,
            balance=new_balance,
            # Keep `initial_balance + Σ movements == balance` after a manual edit.
            initial_balance=self.initial_balance + (new_balance - self.balance),
        )
