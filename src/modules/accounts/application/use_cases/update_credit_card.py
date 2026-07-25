from dataclasses import dataclass

from src.modules.accounts.application.dto.credit_card import CreditCardDTO
from src.modules.accounts.application.dto.credit_card_commands import (
    UpdateCreditCardInputDTO,
)
from src.modules.accounts.application.ports.credit_card_repository import (
    CreditCardRepository,
)
from src.modules.accounts.domain.errors import CreditCardNotFoundError
from src.modules.accounts.domain.validation import (
    clean_color,
    clean_icon,
    clean_name,
    ensure_day_of_month,
    ensure_limit,
    ensure_positive_amount,
)


@dataclass
class UpdateCreditCardUseCase:
    credit_card_repository: CreditCardRepository

    async def execute(self, input_dto: UpdateCreditCardInputDTO) -> CreditCardDTO:
        card = await self.credit_card_repository.find(input_dto.user_id, input_dto.card_id)
        if card is None:
            raise CreditCardNotFoundError()

        updated = card.with_updates(
            name=None if input_dto.name is None else clean_name(input_dto.name),
            icon=None if input_dto.icon is None else clean_icon(input_dto.icon, card.icon),
            color=None if input_dto.color is None else clean_color(input_dto.color, card.color),
            debt=(
                None if input_dto.debt is None else ensure_positive_amount(input_dto.debt, "Debt")
            ),
            limit=None if input_dto.limit is None else ensure_limit(input_dto.limit),
            cutoff_day=(
                None
                if input_dto.cutoff_day is None
                else ensure_day_of_month(input_dto.cutoff_day, "Cutoff day")
            ),
            due_day=(
                None
                if input_dto.due_day is None
                else ensure_day_of_month(input_dto.due_day, "Due day")
            ),
        )
        await self.credit_card_repository.save(updated)
        return CreditCardDTO.from_domain(updated)
