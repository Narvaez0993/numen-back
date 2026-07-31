from dataclasses import dataclass
from uuid import UUID

from src.modules.assistant.domain.errors import PlayExecutionError
from src.modules.goals.application.dto.goal_commands import MoveFundsInputDTO
from src.modules.goals.application.use_cases.contribute import ContributeUseCase
from src.modules.goals.domain.errors import (
    GoalArchivedError,
    GoalNotFoundError,
    InvalidGoalError,
)
from src.modules.movements.domain.errors import (
    InvalidMovementError,
    SourceCurrencyMismatchError,
    SourceNotFoundError,
)


@dataclass
class GoalsGoalContributor:
    """`GoalContributor` through goals' `ContributeUseCase`: the same real
    transfer the goal screen makes, cash-basis deltas and validations included."""

    contribute_use_case: ContributeUseCase

    async def contribute(
        self,
        user_id: UUID,
        *,
        currency: str,
        today: str,
        goal_id: str,
        account_id: str,
        amount: int,
    ) -> None:
        try:
            await self.contribute_use_case.execute(
                MoveFundsInputDTO(
                    user_id=user_id,
                    currency=currency,
                    today=today,
                    goal_id=goal_id,
                    account_id=account_id,
                    amount=amount,
                )
            )
        except (GoalNotFoundError, GoalArchivedError, InvalidGoalError) as exc:
            raise PlayExecutionError("gone") from exc
        except (
            SourceNotFoundError,
            SourceCurrencyMismatchError,
            InvalidMovementError,
        ) as exc:
            raise PlayExecutionError("invalid_account") from exc
