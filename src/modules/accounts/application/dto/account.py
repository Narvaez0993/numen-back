from pydantic import BaseModel

from src.modules.accounts.domain.entities.account import Account


class AccountDTO(BaseModel):
    """Transport shape of an account. `initial_balance` stays internal: it is a
    reconciliation anchor, not something the client should read or show."""

    id: str
    kind: str
    name: str
    sub: str
    icon: str
    color: str
    currency: str
    balance: int

    @classmethod
    def from_domain(cls, account: Account) -> "AccountDTO":
        return cls(
            id=account.id,
            kind=account.kind,
            name=account.name,
            sub=account.sub,
            icon=account.icon,
            color=account.color,
            currency=account.currency,
            balance=account.balance,
        )
