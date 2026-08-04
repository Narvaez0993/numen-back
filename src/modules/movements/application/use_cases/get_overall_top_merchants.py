from dataclasses import dataclass

from src.modules.movements.application.dto.top_merchants import (
    MerchantSpendDTO,
    OverallTopMerchantsInputDTO,
    TopMerchantsOutputDTO,
)
from src.modules.movements.application.ports.movement_repository import MovementRepository
from src.modules.movements.domain.validation import ensure_occurred_on


@dataclass
class GetOverallTopMerchantsUseCase:
    """Where the period's money went, category-blind.

    The sibling of `GetTopMerchantsUseCase`, split instead of flagged: that one's
    `category_id=None` deliberately means the unclassified bucket (budgets' contract),
    so "every category" needs its own question. The assistant's weekly review asks it
    for the week's biggest merchant.
    """

    movement_repository: MovementRepository

    async def execute(self, input_dto: OverallTopMerchantsInputDTO) -> TopMerchantsOutputDTO:
        date_from = ensure_occurred_on(input_dto.date_from)
        date_to = ensure_occurred_on(input_dto.date_to)
        merchants = await self.movement_repository.top_merchants_overall(
            input_dto.user_id, date_from, date_to, input_dto.limit
        )
        return TopMerchantsOutputDTO(
            date_from=date_from,
            date_to=date_to,
            merchants=[MerchantSpendDTO.from_domain(merchant) for merchant in merchants],
        )
