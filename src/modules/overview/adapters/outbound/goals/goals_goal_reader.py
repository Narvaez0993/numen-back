from dataclasses import dataclass
from uuid import UUID

from src.modules.goals.application.dto.goal_commands import TopGoalInputDTO
from src.modules.goals.application.use_cases.get_top_goal import GetTopGoalUseCase
from src.modules.overview.application.ports.goal_reader import TopGoalView


@dataclass
class GoalsGoalReader:
    """`GoalReader` backed by the goals module.

    Calls the narrow use case, not the screen's snapshot: Home needs one pocket, not
    the whole history. The figures come from the same derivations the Metas screen
    uses, so the two can never disagree.
    """

    get_top_goal: GetTopGoalUseCase

    async def top_goal(self, user_id: UUID, today: str) -> TopGoalView | None:
        goal = await self.get_top_goal.execute(TopGoalInputDTO(user_id=user_id, today=today))
        if goal is None:
            return None
        return TopGoalView(
            name=goal.name,
            target=goal.target,
            saved=goal.saved,
            pct=goal.pct,
            projected_on=goal.projected_on,
        )
