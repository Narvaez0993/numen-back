from uuid import UUID

from pydantic import BaseModel

from src.modules.overview.application.ports.budget_reader import GlobalCapView
from src.modules.overview.application.ports.debt_reader import DebtTotalsView
from src.modules.overview.application.ports.goal_reader import TopGoalView
from src.modules.overview.application.ports.movement_summary_reader import (
    RecentMovementView,
)
from src.modules.overview.application.ports.upcoming_charges_reader import UpcomingChargeView


class HomeOverviewInputDTO(BaseModel):
    user_id: UUID
    currency: str
    today: str
    """The client's local day (`YYYY-MM-DD`)."""
    objective: str | None = None
    """What the user came for — decides which figure the hero leads with."""


class PreviousMonthDTO(BaseModel):
    """The same stretch of last month, for a fair comparison mid-month."""

    spent: int
    income: int


class MonthDTO(BaseModel):
    spent: int
    income: int
    saved: int
    """`income - spent`. Negative when the month cost more than it brought in."""
    savings_rate: float
    movements: int
    spent_today: int
    previous: PreviousMonthDTO | None
    change: float | None
    """Signed share of change in spending against `previous`. `None` on a first month —
    a zero there would read as "you spent the same"."""


class PaceDTO(BaseModel):
    """How fast the month is going. `null` in its first days, when a projection would
    be noise rather than information."""

    daily_average: int
    projected: int


class BudgetDTO(BaseModel):
    """The month against the ceiling the user set. `null` when they set none — and the
    daily figure only exists here, because it is only legitimate when it comes from a
    cap they chose.
    """

    target: int
    spent: int
    remaining: int
    """Negative once they are over the cap: reported, not clamped to zero."""
    used: float
    per_day: int | None
    """What is left over the days that are left, **today included**. `null` once the cap
    is spent."""
    projected: int | None
    over: int | None
    """How much past the cap the month would close; `null` when it closes inside."""

    @classmethod
    def from_view(cls, view: GlobalCapView) -> "BudgetDTO":
        return cls(**vars(view))


class DebtsDTO(BaseModel):
    """Money between the user and people. Always present: owing nobody is a real
    measurement, not a missing block — unlike `pace` or `budget`, there is no state in
    which these totals cannot be computed."""

    i_owe: int
    owed_to_me: int
    open_count: int

    @classmethod
    def from_view(cls, view: DebtTotalsView) -> "DebtsDTO":
        return cls(**vars(view))


class GoalDTO(BaseModel):
    """The pocket Home leads with — the active goal closest to done. `null` when no
    goal is active; the saving face then falls back to the month's figures."""

    name: str
    target: int
    saved: int
    pct: float
    projected_on: str | None

    @classmethod
    def from_view(cls, view: TopGoalView) -> "GoalDTO":
        return cls(**vars(view))


class TopCategoryDTO(BaseModel):
    category_id: str | None
    spent: int
    count: int
    share: float
    """Portion of the month's expenses, `0..1`. Not a budget — there is none yet."""


class RecentMovementDTO(BaseModel):
    id: str
    type: str
    description: str
    amount: int
    currency: str
    source_type: str
    source_id: str
    destination_type: str | None
    destination_id: str | None
    category_id: str | None
    occurred_on: str
    captured_via: str
    subscription_id: str | None

    @classmethod
    def from_view(cls, view: RecentMovementView) -> "RecentMovementDTO":
        return cls(**vars(view))


class UpcomingChargeDTO(BaseModel):
    """A recurring charge about to land. `pending` means it is due and waiting for the
    user to confirm; `charge_id` is what confirm/skip act on."""

    subscription_id: str
    charge_on: str
    amount: int
    status: str
    charge_id: str | None

    @classmethod
    def from_view(cls, view: UpcomingChargeView) -> "UpcomingChargeDTO":
        return cls(**vars(view))


class HomeOverviewOutputDTO(BaseModel):
    """The whole Home screen in one read. Amounts in the minor unit of `currency`.

    `focus` is the figure the hero leads with, chosen from the user's objective and the
    data they actually have. Every block is either present with real data or `null`;
    the client never has to guess which one to trust.
    """

    currency: str
    period: str
    days_left: int
    days_elapsed: int
    objective: str | None
    focus: str
    """`start` | `pace` | `debt` | `saving` | `budget` | `invite`."""
    net_balance: int
    accounts_count: int
    credit_cards_count: int
    card_debt: int
    card_limit: int
    month: MonthDTO
    pace: PaceDTO | None
    budget: BudgetDTO | None
    debts: DebtsDTO
    goal: GoalDTO | None
    top_categories: list[TopCategoryDTO]
    recent: list[RecentMovementDTO]
    upcoming: list[UpcomingChargeDTO]
