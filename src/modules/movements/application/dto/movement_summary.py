from uuid import UUID

from pydantic import BaseModel

from src.modules.movements.application.ports.movement_repository import (
    CategorySpend,
    MovementTotals,
)


class SummarizeMovementsInputDTO(BaseModel):
    user_id: UUID
    date_from: str
    date_to: str


class CategorySpendDTO(BaseModel):
    """`category_id: null` is the unclassified bucket."""

    category_id: str | None
    spent: int
    count: int

    @classmethod
    def from_domain(cls, spend: CategorySpend) -> "CategorySpendDTO":
        return cls(category_id=spend.category_id, spent=spend.spent, count=spend.count)


class MovementSummaryOutputDTO(BaseModel):
    """What a period added up to. Amounts in the minor unit of the user's currency.

    Transfers are in `count` but in neither total: paying a card is not spending.
    """

    date_from: str
    date_to: str
    expense_total: int
    income_total: int
    count: int
    by_category: list[CategorySpendDTO]

    @classmethod
    def build(
        cls,
        date_from: str,
        date_to: str,
        totals: MovementTotals,
        by_category: list[CategorySpend],
    ) -> "MovementSummaryOutputDTO":
        return cls(
            date_from=date_from,
            date_to=date_to,
            expense_total=totals.expense_total,
            income_total=totals.income_total,
            count=totals.count,
            by_category=[CategorySpendDTO.from_domain(c) for c in by_category],
        )
