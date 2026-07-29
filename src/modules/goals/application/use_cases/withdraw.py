from dataclasses import dataclass

from src.modules.goals.application.dto.goal import GoalDTO
from src.modules.goals.application.dto.goal_commands import MoveFundsInputDTO
from src.modules.goals.application.ports.funds_reader import FundsReader
from src.modules.goals.application.ports.goal_repository import GoalRepository
from src.modules.goals.application.ports.transfer_recorder import TransferRecorder
from src.modules.goals.domain.errors import GoalInsufficientError, GoalNotFoundError
from src.modules.goals.domain.validation import ensure_amount


@dataclass
class WithdrawUseCase:
    """Money out of the pocket: a real transfer, goal → account.

    This is what closes the loop — reach the goal, take the money back, spend it as
    normal money. A pocket cannot go negative: withdrawing more than it holds is
    `goals.insufficient`, the mirror of a debt's overpayment.
    """

    goal_repository: GoalRepository
    funds_reader: FundsReader
    transfer_recorder: TransferRecorder

    async def execute(self, input_dto: MoveFundsInputDTO) -> GoalDTO:
        goal = await self.goal_repository.find(input_dto.user_id, input_dto.goal_id)
        if goal is None:
            raise GoalNotFoundError()
        amount = ensure_amount(input_dto.amount)

        funds = (await self.funds_reader.funds(input_dto.user_id)).get(goal.id)
        if funds is None or funds.saved < amount:
            raise GoalInsufficientError()

        await self.transfer_recorder.record(
            user_id=input_dto.user_id,
            currency=input_dto.currency,
            description=goal.name,
            amount=amount,
            account_id=input_dto.account_id,
            goal_id=goal.id,
            direction="out",
            occurred_on=input_dto.today,
        )

        fresh = (await self.funds_reader.funds(input_dto.user_id)).get(goal.id)
        return GoalDTO.build(goal, fresh, input_dto.today)
