from uuid import UUID

from pydantic import BaseModel

from src.modules.overview.application.ports.movement_summary_reader import (
    RecentMovementView,
)
from src.modules.overview.application.ports.upcoming_charges_reader import UpcomingChargeView


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
    upcoming: list[UpcomingChargeDTO]
