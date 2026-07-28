from dataclasses import dataclass

from src.modules.goals.application.dto.goal import GoalDTO
from src.modules.goals.application.dto.goal_commands import TopGoalInputDTO
from src.modules.goals.application.ports.funds_reader import FundsReader
from src.modules.goals.application.ports.goal_repository import GoalRepository


@dataclass
class GetTopGoalUseCase:
    """The one pocket Home leads with: the active goal closest to being reached.

    Closest-to-done is the motivating pick — and on Free there is only one active
    goal anyway, so the choice only matters for Plus. `None` when nothing is active,
    and Home falls back to the plain saving face.
    """

    goal_repository: GoalRepository
    funds_reader: FundsReader

    async def execute(self, input_dto: TopGoalInputDTO) -> GoalDTO | None:
        goals = [
            goal
            for goal in await self.goal_repository.list_by_user(input_dto.user_id)
            if goal.active
        ]
        if not goals:
            return None

        funds = await self.funds_reader.funds(input_dto.user_id)
        built = [GoalDTO.build(goal, funds.get(goal.id), input_dto.today) for goal in goals]
        return max(built, key=lambda goal: goal.pct)
