from dataclasses import dataclass

from src.modules.accounts.application.dto.credit_card_commands import (
    DeleteCreditCardInputDTO,
)
from src.modules.accounts.application.ports.credit_card_repository import (
    CreditCardRepository,
)
from src.modules.accounts.domain.errors import CreditCardNotFoundError


@dataclass
class DeleteCreditCardUseCase:
    credit_card_repository: CreditCardRepository

    async def execute(self, input_dto: DeleteCreditCardInputDTO) -> None:
        card = await self.credit_card_repository.find(input_dto.user_id, input_dto.card_id)
        if card is None:
            raise CreditCardNotFoundError()
        await self.credit_card_repository.delete(input_dto.user_id, input_dto.card_id)
