from dataclasses import dataclass

from src.modules.goals.application.dto.goal import GoalDTO
from src.modules.goals.application.dto.goal_commands import MoveFundsInputDTO
from src.modules.goals.application.ports.funds_reader import FundsReader
from src.modules.goals.application.ports.goal_repository import GoalRepository
from src.modules.goals.application.ports.transfer_recorder import TransferRecorder
from src.modules.goals.domain.errors import GoalArchivedError, GoalNotFoundError
from src.modules.goals.domain.validation import ensure_amount


@dataclass
class ContributeUseCase:
    """Money into the pocket: a real transfer, account → goal.

    The recorder validates the account (exists, is the caller's, same currency) the
    way every movement is validated; this use case only owns the pocket-side rules.
    The account balance and the net balance drop — the month's expenses do not: a
    transfer counts to neither total, which is what makes setting money aside
    different from spending it.
    """

    goal_repository: GoalRepository
    funds_reader: FundsReader
    transfer_recorder: TransferRecorder

    async def execute(self, input_dto: MoveFundsInputDTO) -> GoalDTO:
        goal = await self.goal_repository.find(input_dto.user_id, input_dto.goal_id)
        if goal is None:
            raise GoalNotFoundError()
        if not goal.active:
            raise GoalArchivedError()
        amount = ensure_amount(input_dto.amount)

        await self.transfer_recorder.record(
            user_id=input_dto.user_id,
            currency=input_dto.currency,
            description=goal.name,
            amount=amount,
            account_id=input_dto.account_id,
            goal_id=goal.id,
            direction="in",
            occurred_on=input_dto.today,
        )

        funds = (await self.funds_reader.funds(input_dto.user_id)).get(goal.id)
        return GoalDTO.build(goal, funds, input_dto.today)
