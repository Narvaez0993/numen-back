from pydantic import BaseModel

# Amounts are integers in the minor unit of the user's currency.


class DailyResponse(BaseModel):
    available: int
    spent_today: int
    basis: str
    """`budget` | `income` | `none` — the client must be able to say where the
    number comes from instead of presenting it as advice."""


class MonthResponse(BaseModel):
    spent: int
    income: int
    savings_rate: float
    movements: int


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


class HomeOverviewResponse(BaseModel):
    currency: str
    period: str
    days_left: int
    net_balance: int
    accounts_count: int
    credit_cards_count: int
    month: MonthResponse
    daily: DailyResponse
    top_categories: list[TopCategoryResponse]
    recent: list[RecentMovementResponse]
