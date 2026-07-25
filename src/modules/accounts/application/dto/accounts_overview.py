from uuid import UUID

from pydantic import BaseModel

from src.modules.accounts.application.dto.account import AccountDTO
from src.modules.accounts.application.dto.credit_card import CreditCardDTO


class AccountsOverviewInputDTO(BaseModel):
    user_id: UUID
    currency: str


class AccountsOverviewOutputDTO(BaseModel):
    """The Accounts screen in one read (BFF view, not an entity).

    All amounts are in the minor unit of `currency`; v1 pins every source to the
    user's home currency, so the totals are a plain sum.
    """

    currency: str
    accounts: list[AccountDTO]
    credit_cards: list[CreditCardDTO]
    debit_total: int
    cash_total: int
    tc_debt: int
    net_balance: int
    accounts_count: int
    credit_cards_count: int
