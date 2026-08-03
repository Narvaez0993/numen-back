from dataclasses import dataclass
from uuid import UUID

from src.modules.budgets.application.dto.budget_commands import (
    CategoryCapsInputDTO,
    GlobalCapInputDTO,
)
from src.modules.budgets.application.use_cases.get_category_caps import GetCategoryCapsUseCase
from src.modules.budgets.application.use_cases.get_global_cap import GetGlobalCapUseCase
from src.modules.overview.application.ports.budget_reader import CategoryCapView, GlobalCapView


@dataclass
class BudgetsCapReader:
    """`BudgetReader` backed by the budgets module.

    Calls the narrow use cases, not the screen's snapshot: Home needs the ceiling and the
    category caps on every load, and none of the merchant work behind them.
    """

    get_global_cap: GetGlobalCapUseCase
    get_category_caps: GetCategoryCapsUseCase

    async def global_cap(self, user_id: UUID, today: str) -> GlobalCapView | None:
        cap = await self.get_global_cap.execute(GlobalCapInputDTO(user_id=user_id, today=today))
        if cap is None:
            return None
        return GlobalCapView(
            target=cap.target,
            spent=cap.spent,
            remaining=cap.remaining,
            used=cap.used,
            per_day=cap.per_day,
            projected=cap.projected,
            over=cap.over,
        )

    async def category_caps(self, user_id: UUID, today: str) -> dict[str, CategoryCapView]:
        caps = await self.get_category_caps.execute(
            CategoryCapsInputDTO(user_id=user_id, today=today)
        )
        return {cap.category_id: CategoryCapView(target=cap.target, used=cap.used) for cap in caps}
