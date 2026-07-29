from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.goals.application.dto.goal import GoalDTO
from src.modules.goals.application.dto.goal_commands import UpdateGoalInputDTO
from src.modules.goals.application.ports.funds_reader import FundsReader
from src.modules.goals.application.ports.goal_repository import GoalRepository
from src.modules.goals.domain.entities.goal import Goal
from src.modules.goals.domain.errors import (
    GoalLimitReachedError,
    GoalNotEmptyError,
    GoalNotFoundError,
)
from src.modules.goals.domain.validation import ensure_name, ensure_target, ensure_target_date


@dataclass
class UpdateGoalUseCase:
    """Patches what a pocket says, and opens or closes it.

    Closing (`archived: true`) demands the pocket be **empty** — money hidden inside an
    archived goal would be money the app stopped showing. Reopening passes the Free
    gate again: it is an activation, exactly like creating one.
    """

    goal_repository: GoalRepository
    funds_reader: FundsReader
    active_free_limit: int

    async def execute(self, input_dto: UpdateGoalInputDTO) -> GoalDTO:
        goal = await self.goal_repository.find(input_dto.user_id, input_dto.goal_id)
        if goal is None:
            raise GoalNotFoundError()

        funds = (await self.funds_reader.funds(input_dto.user_id)).get(goal.id)
        saved = funds.saved if funds else 0

        updated = self._patched(goal, input_dto)
        if input_dto.archived is True and goal.active:
            if saved > 0:
                raise GoalNotEmptyError()
            updated = updated.with_changes(archived_at=datetime.now(UTC))
        elif input_dto.archived is False and not goal.active:
            if input_dto.tier != "plus":
                existing = await self.goal_repository.list_by_user(input_dto.user_id)
                if sum(1 for g in existing if g.active) >= self.active_free_limit:
                    raise GoalLimitReachedError()
            updated = updated.with_changes(archived_at=None)

        await self.goal_repository.save(updated)
        return GoalDTO.build(updated, funds, input_dto.today)

    @staticmethod
    def _patched(goal: Goal, input_dto: UpdateGoalInputDTO) -> Goal:
        changes: dict[str, object] = {}
        if input_dto.name is not None:
            changes["name"] = ensure_name(input_dto.name)
        if input_dto.target is not None:
            changes["target"] = ensure_target(input_dto.target)
        if input_dto.clear_target_date:
            changes["target_date"] = None
        elif input_dto.target_date is not None:
            changes["target_date"] = ensure_target_date(input_dto.target_date)
        return goal.with_changes(**changes) if changes else goal
