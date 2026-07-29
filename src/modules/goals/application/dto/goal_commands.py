from uuid import UUID

from pydantic import BaseModel


class CreateGoalInputDTO(BaseModel):
    """`tier` gates active pockets; `currency` comes from the caller's preferences."""

    user_id: UUID
    tier: str
    currency: str
    today: str
    name: str
    target: int
    target_date: str | None = None


class UpdateGoalInputDTO(BaseModel):
    """Partial patch: `None` leaves a field untouched. `archived` toggles the pocket —
    closing demands it be empty, reopening passes the Free gate again."""

    user_id: UUID
    tier: str
    goal_id: str
    today: str
    name: str | None = None
    target: int | None = None
    target_date: str | None = None
    clear_target_date: bool = False
    archived: bool | None = None


class DeleteGoalInputDTO(BaseModel):
    user_id: UUID
    goal_id: str


class MoveFundsInputDTO(BaseModel):
    """A contribution or a withdrawal: the pocket, the account on the other end, and
    the amount. `today` stamps the transfer's day."""

    user_id: UUID
    currency: str
    today: str
    goal_id: str
    account_id: str
    amount: int


class GoalsSnapshotInputDTO(BaseModel):
    user_id: UUID
    currency: str
    today: str


class TopGoalInputDTO(BaseModel):
    user_id: UUID
    today: str
