from fastapi import APIRouter, Depends, Query, status

from src.modules.budgets.adapters.inbound.http.schemas import (
    BudgetResponse,
    BudgetsSnapshotResponse,
    CreateBudgetRequest,
    UpdateBudgetRequest,
)
from src.modules.budgets.application.dto.budget_commands import (
    BudgetsSnapshotInputDTO,
    CreateBudgetInputDTO,
    DeleteBudgetInputDTO,
    UpdateBudgetInputDTO,
)
from src.modules.budgets.application.use_cases.create_budget import CreateBudgetUseCase
from src.modules.budgets.application.use_cases.delete_budget import DeleteBudgetUseCase
from src.modules.budgets.application.use_cases.get_budgets_snapshot import (
    GetBudgetsSnapshotUseCase,
)
from src.modules.budgets.application.use_cases.update_budget import UpdateBudgetUseCase
from src.shared.adapters.inbound.http.dependencies import CallerContext, get_caller
from src.shared.adapters.inbound.http.today import resolve_today

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _depends_snapshot_use_case() -> GetBudgetsSnapshotUseCase:
    from src.core.di.container import get_container

    return get_container().get_budgets_snapshot_use_case


def _depends_create_use_case() -> CreateBudgetUseCase:
    from src.core.di.container import get_container

    return get_container().create_budget_use_case


def _depends_update_use_case() -> UpdateBudgetUseCase:
    from src.core.di.container import get_container

    return get_container().update_budget_use_case


def _depends_delete_use_case() -> DeleteBudgetUseCase:
    from src.core.di.container import get_container

    return get_container().delete_budget_use_case


@router.get("/snapshot", response_model=BudgetsSnapshotResponse)
async def get_snapshot(
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: GetBudgetsSnapshotUseCase = Depends(_depends_snapshot_use_case),
) -> BudgetsSnapshotResponse:
    """The Presupuestos screen in one read: the ceiling, the watched categories and
    where their money went. `today` is the caller's local day — the period, the days
    left and therefore the daily ceiling are derived from it."""
    output = await use_case.execute(
        BudgetsSnapshotInputDTO(
            user_id=caller.user_id,
            currency=caller.currency,
            today=resolve_today(today),
        )
    )
    return BudgetsSnapshotResponse(**output.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED, response_model=BudgetResponse)
async def create_budget(
    body: CreateBudgetRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: CreateBudgetUseCase = Depends(_depends_create_use_case),
) -> BudgetResponse:
    """Sets a cap, standing from this month on. A second global one is a conflict
    (there is only one month ceiling); the third watched category is where Free
    stops."""
    output = await use_case.execute(
        CreateBudgetInputDTO(
            user_id=caller.user_id,
            tier=caller.tier,
            today=resolve_today(today),
            scope=body.scope,
            category_id=body.category_id,
            target=body.target,
        )
    )
    return BudgetResponse(**output.model_dump())


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: str,
    body: UpdateBudgetRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: UpdateBudgetUseCase = Depends(_depends_update_use_case),
) -> BudgetResponse:
    """Changes the number. It applies to the month in progress too — that is the
    point of raising a cap on the 12th."""
    output = await use_case.execute(
        UpdateBudgetInputDTO(
            user_id=caller.user_id,
            today=resolve_today(today),
            budget_id=budget_id,
            target=body.target,
        )
    )
    return BudgetResponse(**output.model_dump())


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: str,
    caller: CallerContext = Depends(get_caller),
    use_case: DeleteBudgetUseCase = Depends(_depends_delete_use_case),
) -> None:
    """Stops watching. No movement or balance is touched: a cap never held money."""
    await use_case.execute(DeleteBudgetInputDTO(user_id=caller.user_id, budget_id=budget_id))
