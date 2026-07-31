from dataclasses import dataclass
from uuid import UUID

from src.modules.assistant.application.ports.budgets_reader import (
    BudgetsView,
    CapView,
    CategoryCapView,
)
from src.modules.budgets.application.dto.budget_commands import BudgetsSnapshotInputDTO
from src.modules.budgets.application.use_cases.get_budgets_snapshot import (
    GetBudgetsSnapshotUseCase,
)


@dataclass
class BudgetsBudgetsReader:
    """`BudgetsReader` backed by budgets — the same snapshot the screen reads,
    so the agent can never quote a different ceiling than Presupuestos shows."""

    get_budgets_snapshot: GetBudgetsSnapshotUseCase

    async def snapshot(self, user_id: UUID, currency: str, today: str) -> BudgetsView:
        output = await self.get_budgets_snapshot.execute(
            BudgetsSnapshotInputDTO(user_id=user_id, currency=currency, today=today)
        )
        month = output.month
        return BudgetsView(
            period=output.period,
            days_left=output.days_left,
            month=None
            if month is None
            else CapView(
                id=month.id,
                target=month.target,
                spent=month.spent,
                remaining=month.remaining,
                per_day=month.per_day,
                projected=month.projected,
                over=month.over,
                used=month.used,
            ),
            categories=tuple(
                CategoryCapView(
                    id=c.id,
                    category_id=c.category_id,
                    target=c.target,
                    spent=c.spent,
                    remaining=c.remaining,
                    over=c.over,
                    used=c.used,
                )
                for c in output.categories
            ),
        )
