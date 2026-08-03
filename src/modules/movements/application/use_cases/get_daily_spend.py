from dataclasses import dataclass

from src.modules.movements.application.dto.daily_spend import (
    DailySpendInputDTO,
    DailySpendOutputDTO,
    DaySpendDTO,
)
from src.modules.movements.application.ports.movement_repository import MovementRepository
from src.modules.movements.domain.validation import ensure_occurred_on


@dataclass
class GetDailySpendUseCase:
    """When the money moved, not just where. The assistant's Corte asks this for
    the fun-fact slide (the heaviest day) — same building block shape as
    `GetTopMerchantsUseCase`, aggregated in the store."""

    movement_repository: MovementRepository

    async def execute(self, input_dto: DailySpendInputDTO) -> DailySpendOutputDTO:
        date_from = ensure_occurred_on(input_dto.date_from)
        date_to = ensure_occurred_on(input_dto.date_to)
        days = await self.movement_repository.spend_by_day(input_dto.user_id, date_from, date_to)
        return DailySpendOutputDTO(
            date_from=date_from,
            date_to=date_to,
            days=[DaySpendDTO.from_domain(day) for day in days],
        )
