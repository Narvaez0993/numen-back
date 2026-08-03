from dataclasses import dataclass
from uuid import UUID

from src.modules.assistant.domain.errors import PlayExecutionError
from src.modules.budgets.application.dto.budget_commands import (
    CreateBudgetInputDTO,
    UpdateBudgetInputDTO,
)
from src.modules.budgets.application.use_cases.create_budget import CreateBudgetUseCase
from src.modules.budgets.application.use_cases.update_budget import UpdateBudgetUseCase
from src.modules.budgets.domain.errors import (
    BudgetAlreadyExistsError,
    BudgetCategoryNotFoundError,
    BudgetLimitReachedError,
    BudgetNotFoundError,
    InvalidBudgetError,
)


@dataclass
class BudgetsBudgetWriter:
    """`BudgetWriter` through budgets' own use cases — the Free gate defends
    itself on apply exactly as it does on the budgets screen."""

    create_budget: CreateBudgetUseCase
    update_budget: UpdateBudgetUseCase

    async def create_cap(
        self,
        user_id: UUID,
        *,
        tier: str,
        today: str,
        scope: str,
        category_id: str | None,
        target: int,
    ) -> str:
        try:
            budget = await self.create_budget.execute(
                CreateBudgetInputDTO(
                    user_id=user_id,
                    tier=tier,
                    today=today,
                    scope=scope,
                    category_id=category_id,
                    target=target,
                )
            )
        except BudgetLimitReachedError as exc:
            raise PlayExecutionError("plan_limit") from exc
        except BudgetAlreadyExistsError as exc:
            # Someone set this cap by hand between composition and the tap.
            raise PlayExecutionError("already_exists") from exc
        except (BudgetCategoryNotFoundError, InvalidBudgetError) as exc:
            # The category the play pointed at no longer exists as composed.
            raise PlayExecutionError("gone") from exc
        return budget.id

    async def raise_cap(self, user_id: UUID, *, today: str, budget_id: str, target: int) -> str:
        try:
            budget = await self.update_budget.execute(
                UpdateBudgetInputDTO(
                    user_id=user_id,
                    today=today,
                    budget_id=budget_id,
                    target=target,
                )
            )
        except BudgetNotFoundError as exc:
            raise PlayExecutionError("gone") from exc
        except InvalidBudgetError as exc:
            raise PlayExecutionError("gone") from exc
        return budget.id
