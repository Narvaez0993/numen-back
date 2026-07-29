from dataclasses import dataclass

from src.modules.goals.application.dto.goal_commands import DeleteGoalInputDTO
from src.modules.goals.application.ports.funds_reader import FundsReader
from src.modules.goals.application.ports.goal_repository import GoalRepository
from src.modules.goals.domain.errors import GoalNotEmptyError, GoalNotFoundError


@dataclass
class DeleteGoalUseCase:
    """Forgets a pocket — after it is empty.

    The transfers that funded it stay in Movimientos: they were real money moving, and
    history is not deleted by closing the drawer it pointed at.
    """

    goal_repository: GoalRepository
    funds_reader: FundsReader

    async def execute(self, input_dto: DeleteGoalInputDTO) -> None:
        goal = await self.goal_repository.find(input_dto.user_id, input_dto.goal_id)
        if goal is None:
            raise GoalNotFoundError()

        funds = (await self.funds_reader.funds(input_dto.user_id)).get(goal.id)
        if funds is not None and funds.saved > 0:
            raise GoalNotEmptyError()

        await self.goal_repository.delete(input_dto.user_id, input_dto.goal_id)
