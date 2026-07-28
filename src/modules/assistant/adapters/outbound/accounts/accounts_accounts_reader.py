from dataclasses import dataclass
from uuid import UUID

from src.modules.accounts.application.dto.accounts_overview import AccountsOverviewInputDTO
from src.modules.accounts.application.use_cases.get_accounts_overview import (
    GetAccountsOverviewUseCase,
)
from src.modules.assistant.application.ports.accounts_reader import (
    AccountsView,
    AccountView,
    CreditCardView,
)


@dataclass
class AccountsAccountsReader:
    """`AccountsReader` backed by the accounts module — the same overview the
    screen reads, stripped to the facts a tool payload needs."""

    get_accounts_overview: GetAccountsOverviewUseCase

    async def overview(self, user_id: UUID, currency: str) -> AccountsView:
        output = await self.get_accounts_overview.execute(
            AccountsOverviewInputDTO(user_id=user_id, currency=currency)
        )
        return AccountsView(
            currency=output.currency,
            net_balance=output.net_balance,
            debit_total=output.debit_total,
            cash_total=output.cash_total,
            card_debt_total=output.tc_debt,
            accounts=tuple(
                AccountView(id=a.id, name=a.name, kind=a.kind, balance=a.balance)
                for a in output.accounts
            ),
            credit_cards=tuple(
                CreditCardView(id=c.id, name=c.name, debt=c.debt, limit=c.limit)
                for c in output.credit_cards
            ),
        )
