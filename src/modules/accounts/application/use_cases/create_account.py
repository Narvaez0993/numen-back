from dataclasses import dataclass

from src.modules.accounts.application.dto.account import AccountDTO
from src.modules.accounts.application.dto.account_commands import CreateAccountInputDTO
from src.modules.accounts.application.ports.account_repository import AccountRepository
from src.modules.accounts.domain.entities.account import (
    DEFAULT_COLOR,
    Account,
    default_icon,
)
from src.modules.accounts.domain.errors import AccountLimitReachedError
from src.modules.accounts.domain.validation import (
    clean_color,
    clean_icon,
    clean_name,
    clean_sub,
    ensure_amount,
    ensure_kind,
)
from src.shared.application.ports.clock import Clock


@dataclass
class CreateAccountUseCase:
    account_repository: AccountRepository
    clock: Clock
    free_limit: int

    async def execute(self, input_dto: CreateAccountInputDTO) -> AccountDTO:
        kind = ensure_kind(input_dto.kind)
        name = clean_name(input_dto.name)
        sub = clean_sub(input_dto.sub)
        icon = clean_icon(input_dto.icon, default_icon(kind))
        color = clean_color(input_dto.color, DEFAULT_COLOR)
        balance = ensure_amount(input_dto.balance, "Balance")

        # Names are not unique: two "Nequi" accounts are the user's business, so
        # this read only serves the capacity gate.
        existing = await self.account_repository.list_by_user(input_dto.user_id)
        if input_dto.tier != "plus" and len(existing) >= self.free_limit:
            raise AccountLimitReachedError()

        account = Account.create(
            user_id=input_dto.user_id,
            kind=kind,
            name=name,
            sub=sub,
            icon=icon,
            color=color,
            currency=input_dto.currency,
            balance=balance,
            created_at=self.clock.now(),
        )
        await self.account_repository.save(account)
        return AccountDTO.from_domain(account)
