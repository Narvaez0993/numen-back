from dataclasses import dataclass
from uuid import UUID

from src.modules.goals.application.dto.goal import GoalDTO, GoalsSnapshotDTO
from src.modules.goals.application.dto.goal_commands import GoalsSnapshotInputDTO
from src.modules.goals.application.ports.funds_reader import FundsReader
from src.modules.goals.application.ports.goal_repository import GoalRepository


@dataclass
class GetGoalsSnapshotUseCase:
    """The Metas screen in one read: every pocket with its money and its projection.

    Active pockets first (newest on top), archived history after — the same list, so
    the screen never needs a second request to show the past.
    """

    goal_repository: GoalRepository
    funds_reader: FundsReader

    async def execute(self, input_dto: GoalsSnapshotInputDTO) -> GoalsSnapshotDTO:
        return await self.execute_for(input_dto.user_id, input_dto.currency, input_dto.today)

    async def execute_for(self, user_id: UUID, currency: str, today: str) -> GoalsSnapshotDTO:
        goals = await self.goal_repository.list_by_user(user_id)
        funds = await self.funds_reader.funds(user_id)

        # Newest first, then the stable pass floats active pockets above archived.
        goals.sort(key=lambda goal: goal.created_at, reverse=True)
        goals.sort(key=lambda goal: not goal.active)

        return GoalsSnapshotDTO(
            currency=currency,
            today=today,
            goals=[GoalDTO.build(goal, funds.get(goal.id), today) for goal in goals],
        )
