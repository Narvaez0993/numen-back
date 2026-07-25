from dataclasses import dataclass

from src.modules.accounts.application.dto.credit_card import CreditCardDTO
from src.modules.accounts.application.dto.credit_card_commands import (
    CreateCreditCardInputDTO,
)
from src.modules.accounts.application.ports.credit_card_repository import (
    CreditCardRepository,
)
from src.modules.accounts.domain.entities.credit_card import (
    DEFAULT_CARD_COLOR,
    DEFAULT_CARD_ICON,
    CreditCard,
)
from src.modules.accounts.domain.errors import CreditCardLimitReachedError
from src.modules.accounts.domain.validation import (
    clean_color,
    clean_icon,
    clean_name,
    ensure_day_of_month,
    ensure_limit,
    ensure_positive_amount,
)
from src.shared.application.ports.clock import Clock


@dataclass
class CreateCreditCardUseCase:
    credit_card_repository: CreditCardRepository
    clock: Clock
    free_limit: int

    async def execute(self, input_dto: CreateCreditCardInputDTO) -> CreditCardDTO:
        name = clean_name(input_dto.name)
        icon = clean_icon(input_dto.icon, DEFAULT_CARD_ICON)
        color = clean_color(input_dto.color, DEFAULT_CARD_COLOR)
        debt = ensure_positive_amount(input_dto.debt, "Debt")
        limit = ensure_limit(input_dto.limit)
        cutoff_day = ensure_day_of_month(input_dto.cutoff_day, "Cutoff day")
        due_day = (
            None if input_dto.due_day is None else ensure_day_of_month(input_dto.due_day, "Due day")
        )

        existing = await self.credit_card_repository.list_by_user(input_dto.user_id)
        if input_dto.tier != "plus" and len(existing) >= self.free_limit:
            raise CreditCardLimitReachedError()

        card = CreditCard.create(
            user_id=input_dto.user_id,
            name=name,
            icon=icon,
            color=color,
            currency=input_dto.currency,
            debt=debt,
            limit=limit,
            cutoff_day=cutoff_day,
            due_day=due_day,
            created_at=self.clock.now(),
        )
        await self.credit_card_repository.save(card)
        return CreditCardDTO.from_domain(card)
