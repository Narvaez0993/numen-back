from uuid import UUID

from pydantic import BaseModel

from src.modules.overview.application.ports.movement_summary_reader import (
    RecentMovementView,
)


class HomeOverviewInputDTO(BaseModel):
    user_id: UUID
    currency: str
    today: str
    """The client's local day (`YYYY-MM-DD`)."""


class DailyDTO(BaseModel):
    available: int
    spent_today: int
    basis: str
    """`budget` | `income` | `none` — where `available` comes from."""


class MonthDTO(BaseModel):
    spent: int
    income: int
    savings_rate: float
    movements: int


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

    @classmethod
    def from_view(cls, view: RecentMovementView) -> "RecentMovementDTO":
        return cls(**vars(view))


class HomeOverviewOutputDTO(BaseModel):
    """The whole Home screen in one read. Amounts in the minor unit of `currency`."""

    currency: str
    period: str
    days_left: int
    net_balance: int
    accounts_count: int
    credit_cards_count: int
    month: MonthDTO
    daily: DailyDTO
    top_categories: list[TopCategoryDTO]
    recent: list[RecentMovementDTO]
