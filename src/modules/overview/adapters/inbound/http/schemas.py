from pydantic import BaseModel

# Amounts are integers in the minor unit of the user's currency.


class PreviousMonthResponse(BaseModel):
    spent: int
    income: int


class MonthResponse(BaseModel):
    spent: int
    income: int
    saved: int
    savings_rate: float
    movements: int
    spent_today: int
    previous: PreviousMonthResponse | None
    """The same stretch of last month: July 1-26 against June 1-26, never against the
    whole of June."""
    change: float | None
    """Signed share of change in spending. `null` on a first month."""


class PaceResponse(BaseModel):
    """Where the month lands at the current rate. `null` in the first days, when a
    projection would be noise. It replaced the daily allowance, which rose whenever
    the user held back."""

    daily_average: int
    projected: int


class BudgetResponse(BaseModel):
    """The month against the ceiling the user set; `null` when they set none.

    `per_day` is the only daily figure the payload carries, and it exists because this
    one comes from a number the user chose: it divides what is left by the days that are
    left (**today included**) and it goes down as they spend. The allowance it replaced
    divided their income and went **up** every day they held back.
    """

    target: int
    spent: int
    remaining: int
    """Negative once they are over the cap: reported, not clamped to zero."""
    used: float
    per_day: int | None
    """`null` once the cap is spent — there is nothing left to divide."""
    projected: int | None
    over: int | None
    """How much past the cap the month would close; `null` when it closes inside."""


class DebtsResponse(BaseModel):
    """Money between the user and people, live balances only. `i_owe` joins the card
    debt in the hero's debt face; `owed_to_me` is an asset and stays a separate line."""

    i_owe: int
    owed_to_me: int
    open_count: int


class TopCategoryResponse(BaseModel):
    category_id: str | None
    spent: int
    count: int
    share: float


class RecentMovementResponse(BaseModel):
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


class UpcomingChargeResponse(BaseModel):
    subscription_id: str
    """The client resolves the name and icon from its subscriptions catalog."""
    charge_on: str
    amount: int
    status: str
    """`pending` (due, waiting for confirmation) or `scheduled` (a future date)."""
    charge_id: str | None


class HomeOverviewResponse(BaseModel):
    currency: str
    period: str
    days_left: int
    net_balance: int
    accounts_count: int
    credit_cards_count: int
    days_elapsed: int
    objective: str | None
    focus: str
    """`start` | `pace` | `debt` | `saving` | `budget` | `invite` — which figure the hero
    leads with, chosen from the objective and the data that exists. `invite` means the
    objective's data is missing and the client should ask for it."""
    card_debt: int
    card_limit: int
    month: MonthResponse
    pace: PaceResponse | None
    budget: BudgetResponse | None
    """Present whenever the user set a global cap, whatever `focus` says: with an
    objective of debt or saving the hero leads with that and keeps the cap as a
    secondary row."""
    debts: DebtsResponse
    """Always present — owing nobody is a measurement, not a missing block."""
    top_categories: list[TopCategoryResponse]
    recent: list[RecentMovementResponse]
    upcoming: list[UpcomingChargeResponse]
