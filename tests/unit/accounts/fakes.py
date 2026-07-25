from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.accounts.domain.entities.account import Account, AccountKind
from src.modules.accounts.domain.entities.credit_card import CreditCard

FIXED_NOW = datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return FIXED_NOW


class InMemoryAccountRepository:
    """In-memory `AccountRepository` for use-case unit tests (no Mongo)."""

    def __init__(self, *accounts: Account) -> None:
        self.accounts: list[Account] = list(accounts)

    async def list_by_user(self, user_id: UUID) -> list[Account]:
        return [a for a in self.accounts if a.user_id == user_id]

    async def find(self, user_id: UUID, account_id: str) -> Account | None:
        return next(
            (a for a in self.accounts if a.id == account_id and a.user_id == user_id),
            None,
        )

    async def save(self, account: Account) -> None:
        self.accounts = [a for a in self.accounts if a.id != account.id]
        self.accounts.append(account)

    async def delete(self, user_id: UUID, account_id: str) -> None:
        self.accounts = [
            a for a in self.accounts if not (a.id == account_id and a.user_id == user_id)
        ]


class InMemoryCreditCardRepository:
    def __init__(self, *cards: CreditCard) -> None:
        self.cards: list[CreditCard] = list(cards)

    async def list_by_user(self, user_id: UUID) -> list[CreditCard]:
        return [c for c in self.cards if c.user_id == user_id]

    async def find(self, user_id: UUID, card_id: str) -> CreditCard | None:
        return next((c for c in self.cards if c.id == card_id and c.user_id == user_id), None)

    async def save(self, card: CreditCard) -> None:
        self.cards = [c for c in self.cards if c.id != card.id]
        self.cards.append(card)

    async def delete(self, user_id: UUID, card_id: str) -> None:
        self.cards = [c for c in self.cards if not (c.id == card_id and c.user_id == user_id)]


def make_account(
    user_id: UUID,
    *,
    kind: AccountKind = "debit",
    name: str = "Nequi",
    balance: int = 450_000,
    currency: str = "COP",
) -> Account:
    return Account.create(
        user_id=user_id,
        kind=kind,
        name=name,
        sub="",
        icon="building-bank",
        color="mint",
        currency=currency,
        balance=balance,
        created_at=FIXED_NOW,
    )


def make_card(
    user_id: UUID,
    *,
    name: str = "Visa",
    debt: int = 850_000,
    limit: int = 5_000_000,
    currency: str = "COP",
) -> CreditCard:
    return CreditCard.create(
        user_id=user_id,
        name=name,
        icon="credit-card",
        color="coral",
        currency=currency,
        debt=debt,
        limit=limit,
        cutoff_day=25,
        due_day=5,
        created_at=FIXED_NOW,
    )


def new_user_id() -> UUID:
    return uuid4()
