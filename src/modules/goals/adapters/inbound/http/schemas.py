from pydantic import BaseModel, Field

from src.modules.goals.domain.entities.goal import MAX_NAME_LENGTH

# Amounts are integers in the minor unit of the user's currency, which the server
# owns: no request body carries a currency.


class CreateGoalRequest(BaseModel):
    name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    target: int = Field(gt=0)
    target_date: str | None = None


class UpdateGoalRequest(BaseModel):
    """Absent keys keep their stored value; `target_date` sent as `null` clears it.
    `archived: true` closes the pocket (it must be empty); `false` reopens it
    (passing the Free gate again)."""

    name: str | None = Field(default=None, min_length=1, max_length=MAX_NAME_LENGTH)
    target: int | None = Field(default=None, gt=0)
    target_date: str | None = None
    archived: bool | None = None


class MoveFundsRequest(BaseModel):
    """A contribution or a withdrawal: the account on the other end, and how much."""

    account_id: str
    amount: int = Field(gt=0)


class GoalResponse(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    target: int
    target_date: str | None
    archived: bool
    saved: int
    """Σ of the transfer movements in minus out — never a stored figure."""
    pct: float
    achieved: bool
    projected_on: str | None
    """`YYYY-MM` the goal lands at the current contribution pace; `null` without
    contributions or once reached. The client names the month."""
    needed_per_month: int | None
    """What each remaining month needs to land on `target_date`; `null` without one."""
    monthly_pace: int | None


class GoalsSnapshotResponse(BaseModel):
    currency: str
    today: str
    goals: list[GoalResponse]
    """Active pockets first (newest on top), archived history after."""
