from fastapi import APIRouter, Depends, Header, Query, status

from src.modules.movements.adapters.inbound.http.schemas import (
    CreateMovementRequest,
    MovementResponse,
    MovementsListResponse,
)
from src.modules.movements.application.dto.list_movements import ListMovementsInputDTO
from src.modules.movements.application.dto.movement_commands import CreateMovementInputDTO
from src.modules.movements.application.use_cases.create_movement import CreateMovementUseCase
from src.modules.movements.application.use_cases.list_movements import ListMovementsUseCase
from src.shared.adapters.inbound.http.dependencies import CallerContext, get_caller

router = APIRouter(prefix="/movements", tags=["movements"])


def _depends_create_use_case() -> CreateMovementUseCase:
    from src.core.di.container import get_container

    return get_container().create_movement_use_case


def _depends_list_use_case() -> ListMovementsUseCase:
    from src.core.di.container import get_container

    return get_container().list_movements_use_case


@router.get("", response_model=MovementsListResponse)
async def list_movements(
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
    type: str | None = Query(default=None),
    source_id: str | None = Query(default=None, alias="source"),
    category_id: str | None = Query(default=None, alias="category"),
    limit: int = Query(default=100, ge=1, le=200),
    caller: CallerContext = Depends(get_caller),
    use_case: ListMovementsUseCase = Depends(_depends_list_use_case),
) -> MovementsListResponse:
    output = await use_case.execute(
        ListMovementsInputDTO(
            user_id=caller.user_id,
            date_from=date_from,
            date_to=date_to,
            type=type,
            source_id=source_id,
            category_id=category_id,
            limit=limit,
        )
    )
    return MovementsListResponse(**output.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MovementResponse)
async def create_movement(
    body: CreateMovementRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    caller: CallerContext = Depends(get_caller),
    use_case: CreateMovementUseCase = Depends(_depends_create_use_case),
) -> MovementResponse:
    """Registers the movement and moves the money atomically.

    Sending the same `Idempotency-Key` twice returns the original movement instead
    of creating a second one — a double tap on "save" must not cost money twice.
    """
    output = await use_case.execute(
        CreateMovementInputDTO(
            user_id=caller.user_id,
            currency=caller.currency,
            type=body.type,
            description=body.description,
            amount=body.amount,
            source_type=body.source_type,
            source_id=body.source_id,
            destination_type=body.destination_type,
            destination_id=body.destination_id,
            category_id=body.category_id,
            occurred_on=body.occurred_on,
            captured_via=body.captured_via,
            idempotency_key=idempotency_key,
        )
    )
    return MovementResponse(**output.model_dump())
