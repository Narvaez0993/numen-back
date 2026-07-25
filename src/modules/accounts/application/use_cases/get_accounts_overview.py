from dataclasses import dataclass

from src.modules.accounts.application.dto.account import AccountDTO
from src.modules.accounts.application.dto.accounts_overview import (
    AccountsOverviewInputDTO,
    AccountsOverviewOutputDTO,
)
from src.modules.accounts.application.dto.credit_card import CreditCardDTO
from src.modules.accounts.application.ports.account_repository import AccountRepository
from src.modules.accounts.application.ports.credit_card_repository import (
    CreditCardRepository,
)


@dataclass
class GetAccountsOverviewUseCase:
    """Single read behind the Accounts screen: two indexed queries, totals here.

    The aggregates are derived, never persisted — a stored total is one more
    thing that can drift out of sync with its parts.
    """

    account_repository: AccountRepository
    credit_card_repository: CreditCardRepository

    async def execute(self, input_dto: AccountsOverviewInputDTO) -> AccountsOverviewOutputDTO:
        accounts = await self.account_repository.list_by_user(input_dto.user_id)
        cards = await self.credit_card_repository.list_by_user(input_dto.user_id)

        debit_total = sum(a.balance for a in accounts if a.kind == "debit")
        cash_total = sum(a.balance for a in accounts if a.kind == "cash")
        tc_debt = sum(c.debt for c in cards)

        return AccountsOverviewOutputDTO(
            currency=input_dto.currency,
            accounts=[AccountDTO.from_domain(a) for a in accounts],
            credit_cards=[CreditCardDTO.from_domain(c) for c in cards],
            debit_total=debit_total,
            cash_total=cash_total,
            tc_debt=tc_debt,
            net_balance=debit_total + cash_total - tc_debt,
            accounts_count=len(accounts),
            credit_cards_count=len(cards),
        )
