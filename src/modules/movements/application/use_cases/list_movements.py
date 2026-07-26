from dataclasses import dataclass

from src.modules.movements.application.dto.list_movements import (
    ListMovementsInputDTO,
    ListMovementsOutputDTO,
)
from src.modules.movements.application.dto.movement import MovementDTO
from src.modules.movements.application.ports.movement_repository import (
    MovementQuery,
    MovementRepository,
)
from src.modules.movements.domain.validation import ensure_occurred_on, ensure_type

MAX_LIMIT = 200


@dataclass
class ListMovementsUseCase:
    movement_repository: MovementRepository

    async def execute(self, input_dto: ListMovementsInputDTO) -> ListMovementsOutputDTO:
        query = MovementQuery(
            user_id=input_dto.user_id,
            date_from=(
                None if input_dto.date_from is None else ensure_occurred_on(input_dto.date_from)
            ),
            date_to=(None if input_dto.date_to is None else ensure_occurred_on(input_dto.date_to)),
            type=None if input_dto.type is None else ensure_type(input_dto.type),
            source_id=input_dto.source_id,
            category_id=input_dto.category_id,
            limit=max(1, min(input_dto.limit, MAX_LIMIT)),
        )
        movements = await self.movement_repository.search(query)
        return ListMovementsOutputDTO(movements=[MovementDTO.from_domain(m) for m in movements])
