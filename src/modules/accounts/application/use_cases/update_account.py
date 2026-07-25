from dataclasses import dataclass

from src.modules.accounts.application.dto.account import AccountDTO
from src.modules.accounts.application.dto.account_commands import UpdateAccountInputDTO
from src.modules.accounts.application.ports.account_repository import AccountRepository
from src.modules.accounts.domain.errors import AccountNotFoundError
from src.modules.accounts.domain.validation import (
    clean_color,
    clean_icon,
    clean_name,
    clean_sub,
    ensure_amount,
)


@dataclass
class UpdateAccountUseCase:
    account_repository: AccountRepository

    async def execute(self, input_dto: UpdateAccountInputDTO) -> AccountDTO:
        account = await self.account_repository.find(input_dto.user_id, input_dto.account_id)
        if account is None:
            raise AccountNotFoundError()

        updated = account.with_updates(
            name=None if input_dto.name is None else clean_name(input_dto.name),
            sub=None if input_dto.sub is None else clean_sub(input_dto.sub),
            icon=None if input_dto.icon is None else clean_icon(input_dto.icon, account.icon),
            color=None if input_dto.color is None else clean_color(input_dto.color, account.color),
            balance=(
                None if input_dto.balance is None else ensure_amount(input_dto.balance, "Balance")
            ),
        )
        await self.account_repository.save(updated)
        return AccountDTO.from_domain(updated)
