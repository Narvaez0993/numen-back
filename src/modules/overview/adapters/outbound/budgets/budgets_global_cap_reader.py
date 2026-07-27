from dataclasses import dataclass
from uuid import UUID

from src.modules.budgets.application.dto.budget_commands import GlobalCapInputDTO
from src.modules.budgets.application.use_cases.get_global_cap import GetGlobalCapUseCase
from src.modules.overview.application.ports.budget_reader import GlobalCapView


@dataclass
class BudgetsGlobalCapReader:
    """`BudgetReader` backed by the budgets module.

    Calls the narrow use case, not the screen's snapshot: Home needs the ceiling on every
    load and none of the per category work behind it.
    """

    get_global_cap: GetGlobalCapUseCase

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
