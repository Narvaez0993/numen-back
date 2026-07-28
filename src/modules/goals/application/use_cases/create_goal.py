from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.goals.application.dto.goal import GoalDTO
from src.modules.goals.application.dto.goal_commands import CreateGoalInputDTO
from src.modules.goals.application.ports.goal_repository import GoalRepository
from src.modules.goals.domain.entities.goal import Goal
from src.modules.goals.domain.errors import GoalLimitReachedError
from src.modules.goals.domain.validation import ensure_name, ensure_target, ensure_target_date


@dataclass
class CreateGoalUseCase:
    """Opens a pocket. The plan gates how many can be **open at once**.

    Archived pockets never count against the gate — closing a finished goal is exactly
    how a Free user starts the next one.
    """

    goal_repository: GoalRepository
    active_free_limit: int

    async def execute(self, input_dto: CreateGoalInputDTO) -> GoalDTO:
        name = ensure_name(input_dto.name)
        target = ensure_target(input_dto.target)
        target_date = ensure_target_date(input_dto.target_date)

        if input_dto.tier != "plus":
            existing = await self.goal_repository.list_by_user(input_dto.user_id)
            if sum(1 for goal in existing if goal.active) >= self.active_free_limit:
                raise GoalLimitReachedError()

        goal = Goal.create(
            user_id=input_dto.user_id,
            name=name,
            target=target,
            currency=input_dto.currency,
            target_date=target_date,
            created_at=datetime.now(UTC),
        )
        await self.goal_repository.save(goal)
        return GoalDTO.build(goal, None, input_dto.today)
