from dataclasses import dataclass

from src.modules.movements.application.dto.top_merchants import (
    MerchantSpendDTO,
    TopMerchantsInputDTO,
    TopMerchantsOutputDTO,
)
from src.modules.movements.application.ports.movement_repository import MovementRepository
from src.modules.movements.domain.validation import ensure_occurred_on


@dataclass
class GetTopMerchantsUseCase:
    """Where the money of a category went, grouped by what the user typed.

    Same shape of building block as `SummarizeMovementsUseCase`: budgets asks it what
    filled up a category cap, and the assistant's insights will ask it the same thing.
    There is no merchant entity behind it — the grouping is over free text, which is why
    it lives with the collection that owns the descriptions.
    """

    movement_repository: MovementRepository

    async def execute(self, input_dto: TopMerchantsInputDTO) -> TopMerchantsOutputDTO:
        date_from = ensure_occurred_on(input_dto.date_from)
        date_to = ensure_occurred_on(input_dto.date_to)
        merchants = await self.movement_repository.top_merchants(
            input_dto.user_id,
            date_from,
            date_to,
            input_dto.category_id,
            input_dto.limit,
        )
        return TopMerchantsOutputDTO(
            date_from=date_from,
            date_to=date_to,
            merchants=[MerchantSpendDTO.from_domain(merchant) for merchant in merchants],
        )
