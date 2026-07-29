from dataclasses import dataclass

from src.modules.movements.application.dto.goal_funds import (
    GoalFundsDTO,
    GoalFundsInputDTO,
    GoalFundsOutputDTO,
)
from src.modules.movements.application.ports.movement_repository import MovementRepository


@dataclass
class GetGoalFundsUseCase:
    """What each goal's pocket holds — summed from the transfers themselves.

    The building block the goals module reads through its port. It lives here because
    the transfers are this module's rows: a pocket has no stored balance to ask, and
    that is the point — a sum of movements cannot drift from the movements.
    """

    movement_repository: MovementRepository

    async def execute(self, input_dto: GoalFundsInputDTO) -> GoalFundsOutputDTO:
        funds = await self.movement_repository.goal_funds(input_dto.user_id)
        return GoalFundsOutputDTO(funds=[GoalFundsDTO.from_domain(row) for row in funds])
