from fastapi import APIRouter, Depends, Query, status

from src.modules.goals.adapters.inbound.http.schemas import (
    CreateGoalRequest,
    GoalResponse,
    GoalsSnapshotResponse,
    MoveFundsRequest,
    UpdateGoalRequest,
)
from src.modules.goals.application.dto.goal_commands import (
    CreateGoalInputDTO,
    DeleteGoalInputDTO,
    GoalsSnapshotInputDTO,
    MoveFundsInputDTO,
    UpdateGoalInputDTO,
)
from src.modules.goals.application.use_cases.contribute import ContributeUseCase
from src.modules.goals.application.use_cases.create_goal import CreateGoalUseCase
from src.modules.goals.application.use_cases.delete_goal import DeleteGoalUseCase
from src.modules.goals.application.use_cases.get_goals_snapshot import (
    GetGoalsSnapshotUseCase,
)
from src.modules.goals.application.use_cases.update_goal import UpdateGoalUseCase
from src.modules.goals.application.use_cases.withdraw import WithdrawUseCase
from src.shared.adapters.inbound.http.dependencies import CallerContext, get_caller
from src.shared.adapters.inbound.http.today import resolve_today

router = APIRouter(prefix="/goals", tags=["goals"])


def _depends_snapshot() -> GetGoalsSnapshotUseCase:
    from src.core.di.container import get_container

    return get_container().get_goals_snapshot_use_case


def _depends_create() -> CreateGoalUseCase:
    from src.core.di.container import get_container

    return get_container().create_goal_use_case


def _depends_update() -> UpdateGoalUseCase:
    from src.core.di.container import get_container

    return get_container().update_goal_use_case


def _depends_delete() -> DeleteGoalUseCase:
    from src.core.di.container import get_container

    return get_container().delete_goal_use_case


def _depends_contribute() -> ContributeUseCase:
    from src.core.di.container import get_container

    return get_container().contribute_use_case


def _depends_withdraw() -> WithdrawUseCase:
    from src.core.di.container import get_container

    return get_container().withdraw_use_case


@router.get("/snapshot", response_model=GoalsSnapshotResponse)
async def get_snapshot(
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: GetGoalsSnapshotUseCase = Depends(_depends_snapshot),
) -> GoalsSnapshotResponse:
    """The Metas screen in one read. `today` is the caller's local day — the
    contribution-pace projection is derived from it, never stored."""
    output = await use_case.execute(
        GoalsSnapshotInputDTO(
            user_id=caller.user_id,
            currency=caller.currency,
            today=resolve_today(today),
        )
    )
    return GoalsSnapshotResponse(**output.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED, response_model=GoalResponse)
async def create_goal(
    body: CreateGoalRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: CreateGoalUseCase = Depends(_depends_create),
) -> GoalResponse:
    """Opens a pocket. Free keeps one active at a time — archived ones never count."""
    output = await use_case.execute(
        CreateGoalInputDTO(
            user_id=caller.user_id,
            tier=caller.tier,
            currency=caller.currency,
            today=resolve_today(today),
            name=body.name,
            target=body.target,
            target_date=body.target_date,
        )
    )
    return GoalResponse(**output.model_dump())


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    body: UpdateGoalRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: UpdateGoalUseCase = Depends(_depends_update),
) -> GoalResponse:
    """Patches the pocket; `archived` closes (empty only) or reopens it."""
    fields = body.model_fields_set
    output = await use_case.execute(
        UpdateGoalInputDTO(
            user_id=caller.user_id,
            tier=caller.tier,
            goal_id=goal_id,
            today=resolve_today(today),
            name=body.name,
            target=body.target,
            target_date=body.target_date,
            clear_target_date="target_date" in fields and body.target_date is None,
            archived=body.archived,
        )
    )
    return GoalResponse(**output.model_dump())


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: str,
    caller: CallerContext = Depends(get_caller),
    use_case: DeleteGoalUseCase = Depends(_depends_delete),
) -> None:
    """Forgets an **empty** pocket. Its transfers stay in Movimientos — they were
    real money moving."""
    await use_case.execute(DeleteGoalInputDTO(user_id=caller.user_id, goal_id=goal_id))


@router.post("/{goal_id}/contributions", response_model=GoalResponse)
async def contribute(
    goal_id: str,
    body: MoveFundsRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: ContributeUseCase = Depends(_depends_contribute),
) -> GoalResponse:
    """Money into the pocket: a real transfer — the account and the net balance drop,
    the month's expenses do not."""
    output = await use_case.execute(
        MoveFundsInputDTO(
            user_id=caller.user_id,
            currency=caller.currency,
            today=resolve_today(today),
            goal_id=goal_id,
            account_id=body.account_id,
            amount=body.amount,
        )
    )
    return GoalResponse(**output.model_dump())


@router.post("/{goal_id}/withdrawals", response_model=GoalResponse)
async def withdraw(
    goal_id: str,
    body: MoveFundsRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: WithdrawUseCase = Depends(_depends_withdraw),
) -> GoalResponse:
    """Money out of the pocket, back to an account. More than it holds →
    `goals.insufficient`."""
    output = await use_case.execute(
        MoveFundsInputDTO(
            user_id=caller.user_id,
            currency=caller.currency,
            today=resolve_today(today),
            goal_id=goal_id,
            account_id=body.account_id,
            amount=body.amount,
        )
    )
    return GoalResponse(**output.model_dump())
