from pydantic import BaseModel

from src.modules.goals.application.ports.funds_reader import PocketFunds
from src.modules.goals.domain import projection
from src.modules.goals.domain.entities.goal import Goal


class GoalDTO(BaseModel):
    """A pocket as the client reads it. Everything under `target_date` is derived —
    from the transfers (saved) and from today (the projections) — never stored."""

    id: str
    name: str
    icon: str
    color: str
    target: int
    target_date: str | None
    archived: bool
    saved: int
    pct: float
    achieved: bool
    projected_on: str | None
    """`YYYY-MM` the goal lands at the current pace; the client names the month."""
    needed_per_month: int | None
    monthly_pace: int | None

    @classmethod
    def build(cls, goal: Goal, funds: PocketFunds | None, today: str) -> "GoalDTO":
        saved = funds.saved if funds else 0
        first_in_on = funds.first_in_on if funds else None
        pace = (
            projection.monthly_pace(saved=saved, first_in_on=first_in_on, today=today)
            if first_in_on is not None and saved > 0
            else None
        )
        return cls(
            id=goal.id,
            name=goal.name,
            icon=goal.icon,
            color=goal.color,
            target=goal.target,
            target_date=goal.target_date,
            archived=not goal.active,
            saved=saved,
            pct=saved / goal.target if goal.target > 0 else 0.0,
            achieved=saved >= goal.target,
            projected_on=projection.projected_on(
                saved=saved, target=goal.target, first_in_on=first_in_on, today=today
            ),
            needed_per_month=projection.needed_per_month(
                saved=saved, target=goal.target, target_date=goal.target_date, today=today
            ),
            monthly_pace=pace,
        )


class GoalsSnapshotDTO(BaseModel):
    """The Metas screen in one read: active pockets first, archived history after."""

    currency: str
    today: str
    goals: list[GoalDTO]
