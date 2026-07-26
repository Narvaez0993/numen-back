from dataclasses import dataclass

from src.modules.movements.application.dto.movement_summary import (
    MovementSummaryOutputDTO,
    SummarizeMovementsInputDTO,
)
from src.modules.movements.application.ports.movement_repository import MovementRepository
from src.modules.movements.domain.validation import ensure_occurred_on


@dataclass
class SummarizeMovementsUseCase:
    """What a date range added up to, aggregated by the store.

    Building block, not a private calculation of Home: budgets (their spent vs
    target) and the assistant's rule-based insights read the same numbers.
    """

    movement_repository: MovementRepository

    async def execute(self, input_dto: SummarizeMovementsInputDTO) -> MovementSummaryOutputDTO:
        date_from = ensure_occurred_on(input_dto.date_from)
        date_to = ensure_occurred_on(input_dto.date_to)
        totals = await self.movement_repository.totals(input_dto.user_id, date_from, date_to)
        by_category = await self.movement_repository.spend_by_category(
            input_dto.user_id, date_from, date_to
        )
        return MovementSummaryOutputDTO.build(date_from, date_to, totals, by_category)
