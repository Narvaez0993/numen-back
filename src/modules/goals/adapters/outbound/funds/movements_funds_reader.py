from dataclasses import dataclass
from uuid import UUID

from src.modules.goals.application.ports.funds_reader import PocketFunds
from src.modules.movements.application.dto.goal_funds import GoalFundsInputDTO
from src.modules.movements.application.use_cases.get_goal_funds import GetGoalFundsUseCase


@dataclass
class MovementsFundsReader:
    """`FundsReader` backed by the movements module.

    Talks to its use case, never to its collection: the sum lives with the rows that
    make it up, and this is only the translation into what a pocket needs.
    """

    get_goal_funds: GetGoalFundsUseCase

    async def funds(self, user_id: UUID) -> dict[str, PocketFunds]:
        output = await self.get_goal_funds.execute(GoalFundsInputDTO(user_id=user_id))
        return {
            row.goal_id: PocketFunds(
                goal_id=row.goal_id, saved=row.saved, first_in_on=row.first_in_on
            )
            for row in output.funds
        }
