from dataclasses import dataclass
from uuid import UUID

from src.modules.accounts.application.dto.accounts_overview import (
    AccountsOverviewInputDTO,
)
from src.modules.accounts.application.use_cases.get_accounts_overview import (
    GetAccountsOverviewUseCase,
)
from src.modules.overview.application.ports.balance_reader import BalanceSnapshot


@dataclass
class AccountsBalanceReader:
    """`BalanceReader` backed by the accounts module.

    Reuses the overview use case that the Accounts screen already calls, so the
    net balance shown on Home is computed by exactly one formula in the codebase.
    """

    accounts_overview: GetAccountsOverviewUseCase

    async def read(self, user_id: UUID, currency: str) -> BalanceSnapshot:
        overview = await self.accounts_overview.execute(
            AccountsOverviewInputDTO(user_id=user_id, currency=currency)
        )
        return BalanceSnapshot(
            net_balance=overview.net_balance,
            accounts_count=overview.accounts_count,
            credit_cards_count=overview.credit_cards_count,
        )
