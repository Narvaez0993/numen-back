from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from src.modules.budgets.application.dto.budget import BudgetDTO
from src.modules.budgets.application.dto.budget_commands import CreateBudgetInputDTO
from src.modules.budgets.application.ports.budget_repository import BudgetRepository
from src.modules.budgets.application.ports.category_reader import CategoryReader
from src.modules.budgets.domain.entities.budget import (
    ALLOWED_SCOPES,
    MAX_TARGET,
    MIN_TARGET,
    Budget,
    Scope,
)
from src.modules.budgets.domain.errors import (
    BudgetAlreadyExistsError,
    BudgetCategoryNotFoundError,
    BudgetLimitReachedError,
    InvalidBudgetError,
)


@dataclass
class CreateBudgetUseCase:
    """Sets a cap. The plan gates how many **categories** can be watched.

    There is no gate on the global one: a user has a single month ceiling by definition,
    so a second one is a conflict, not an upsell. Free watches
    `category_free_limit` categories, Plus as many as it likes.
    """

    budget_repository: BudgetRepository
    category_reader: CategoryReader
    category_free_limit: int

    async def execute(self, input_dto: CreateBudgetInputDTO) -> BudgetDTO:
        if input_dto.scope not in ALLOWED_SCOPES:
            raise InvalidBudgetError(f"Invalid scope: {input_dto.scope}")
        if not MIN_TARGET <= input_dto.target <= MAX_TARGET:
            raise InvalidBudgetError("A cap has to be a positive amount")
        scope = cast(Scope, input_dto.scope)

        existing = await self.budget_repository.list_by_user(input_dto.user_id)

        if scope == "global":
            if any(budget.scope == "global" for budget in existing):
                raise BudgetAlreadyExistsError()
            category_id = None
        else:
            category_id = (input_dto.category_id or "").strip()
            if not category_id:
                raise InvalidBudgetError("A category cap needs a category")
            if not await self.category_reader.exists(input_dto.user_id, category_id):
                raise BudgetCategoryNotFoundError()

            watched = [budget for budget in existing if budget.scope == "category"]
            if any(budget.category_id == category_id for budget in watched):
                raise BudgetAlreadyExistsError()
            if input_dto.tier != "plus" and len(watched) >= self.category_free_limit:
                raise BudgetLimitReachedError()

        budget = Budget.create(
            user_id=input_dto.user_id,
            scope=scope,
            category_id=category_id,
            target=input_dto.target,
            since=input_dto.today[:7],
            created_at=datetime.now(UTC),
        )
        await self.budget_repository.save(budget)
        return BudgetDTO.from_domain(budget)
