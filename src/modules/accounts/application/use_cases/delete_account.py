from dataclasses import dataclass

from src.modules.accounts.application.dto.account_commands import DeleteAccountInputDTO
from src.modules.accounts.application.ports.account_repository import AccountRepository
from src.modules.accounts.domain.errors import AccountNotFoundError


@dataclass
class DeleteAccountUseCase:
    account_repository: AccountRepository

    async def execute(self, input_dto: DeleteAccountInputDTO) -> None:
        account = await self.account_repository.find(input_dto.user_id, input_dto.account_id)
        if account is None:
            raise AccountNotFoundError()
        await self.account_repository.delete(input_dto.user_id, input_dto.account_id)
