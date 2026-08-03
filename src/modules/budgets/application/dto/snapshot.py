from pydantic import BaseModel

from src.modules.budgets.application.dto.budget import CapDTO
from src.modules.budgets.application.ports.spend_reader import MerchantSpendView
from src.modules.budgets.domain.entities.budget import Budget
from src.modules.budgets.domain.spending_cap import CapProgress


class MerchantDTO(BaseModel):
    """A merchant as the user wrote it — there is no catalog behind this."""

    label: str
    spent: int
    count: int

    @classmethod
    def from_view(cls, view: MerchantSpendView) -> "MerchantDTO":
        return cls(label=view.label, spent=view.spent, count=view.count)


class CategoryCapProgressDTO(CapDTO):
    """A category cap measured, without the merchants behind it — what Home needs to put
    a category's spending against the limit its owner set."""

    category_id: str

    @classmethod
    def for_category(cls, budget: Budget, cap: CapProgress) -> "CategoryCapProgressDTO":
        return cls(**CapDTO.build(budget, cap).model_dump(), category_id=str(budget.category_id))


class CategoryCapDTO(CapDTO):
    """A category cap. Travels with the **id**, never the name: the client resolves the
    label from the catalog it already caches, so renaming a category updates this screen
    for free."""

    category_id: str
    count: int
    top_merchants: list[MerchantDTO]

    @classmethod
    def for_category(
        cls,
        budget: Budget,
        cap: CapProgress,
        *,
        count: int,
        merchants: list[MerchantSpendView],
    ) -> "CategoryCapDTO":
        return cls(
            **CapDTO.build(budget, cap).model_dump(),
            category_id=str(budget.category_id),
            count=count,
            top_merchants=[MerchantDTO.from_view(view) for view in merchants],
        )


class BudgetsSnapshotDTO(BaseModel):
    """The Presupuestos screen in one read.

    `month` is the global ceiling — `null` for someone who has not set one, so the
    screen shows its empty state instead of a $0 cap they would appear to have blown on
    day one.

    The caps are **not additive**: each category cap warns about its own spending while
    every expense still counts against `month`. Summing them would invent a budget the
    user never set.
    """

    currency: str
    period: str
    days_left: int
    days_elapsed: int
    month: CapDTO | None
    categories: list[CategoryCapDTO]
