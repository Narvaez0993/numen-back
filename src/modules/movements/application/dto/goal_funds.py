from uuid import UUID

from pydantic import BaseModel

from src.modules.movements.application.ports.movement_repository import GoalFunds


class GoalFundsInputDTO(BaseModel):
    user_id: UUID


class GoalFundsDTO(BaseModel):
    goal_id: str
    saved: int
    first_in_on: str | None

    @classmethod
    def from_domain(cls, funds: GoalFunds) -> "GoalFundsDTO":
        return cls(goal_id=funds.goal_id, saved=funds.saved, first_in_on=funds.first_in_on)


class GoalFundsOutputDTO(BaseModel):
    """What every pocket holds, straight from the transfers that filled it."""

    funds: list[GoalFundsDTO]
