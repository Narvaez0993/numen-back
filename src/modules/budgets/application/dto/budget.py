from pydantic import BaseModel

from src.modules.budgets.domain.entities.budget import Budget
from src.modules.budgets.domain.spending_cap import CapProgress


class BudgetDTO(BaseModel):
    """A cap as the client reads it. `target` is in the minor unit of the user's
    currency, and `since` is the month its current value was set in."""

    id: str
    scope: str
    category_id: str | None
    target: int
    since: str

    @classmethod
    def from_domain(cls, budget: Budget) -> "BudgetDTO":
        return cls(
            id=budget.id,
            scope=budget.scope,
            category_id=budget.category_id,
            target=budget.target,
            since=budget.since,
        )


class CapDTO(BaseModel):
    """The month measured against a cap — every field derived, nothing stored.

    `remaining` goes negative and `over` stays `null` while the month closes inside the
    cap: the client only alarms about a real number.
    """

    id: str
    target: int
    spent: int
    remaining: int
    used: float
    per_day: int | None
    projected: int | None
    over: int | None

    @classmethod
    def build(cls, budget: Budget, cap: CapProgress) -> "CapDTO":
        return cls(
            id=budget.id,
            target=cap.target,
            spent=cap.spent,
            remaining=cap.remaining,
            used=cap.used,
            per_day=cap.per_day,
            projected=cap.projected,
            over=cap.over,
        )
