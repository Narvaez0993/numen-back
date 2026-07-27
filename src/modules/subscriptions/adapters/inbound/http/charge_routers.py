from fastapi import APIRouter, Depends, Query

from src.modules.subscriptions.adapters.inbound.http.charge_schemas import (
    ChargeResponse,
    ChargesListResponse,
    ConfirmChargeRequest,
)
from src.modules.subscriptions.application.dto.charge import (
    ListChargesInputDTO,
    SettleChargeInputDTO,
)
from src.modules.subscriptions.application.use_cases.confirm_charge import ConfirmChargeUseCase
from src.modules.subscriptions.application.use_cases.list_charges import ListChargesUseCase
from src.modules.subscriptions.application.use_cases.skip_charge import SkipChargeUseCase
from src.shared.adapters.inbound.http.dependencies import CallerContext, get_caller

router = APIRouter(prefix="/subscription-charges", tags=["subscriptions"])


def _depends_list_use_case() -> ListChargesUseCase:
    from src.core.di.container import get_container

    return get_container().list_charges_use_case


def _depends_confirm_use_case() -> ConfirmChargeUseCase:
    from src.core.di.container import get_container

    return get_container().confirm_charge_use_case


def _depends_skip_use_case() -> SkipChargeUseCase:
    from src.core.di.container import get_container

    return get_container().skip_charge_use_case


@router.get("", response_model=ChargesListResponse)
async def list_charges(
    status_filter: str | None = Query(default=None, alias="status"),
    caller: CallerContext = Depends(get_caller),
    use_case: ListChargesUseCase = Depends(_depends_list_use_case),
) -> ChargesListResponse:
    """Charges of the caller. `?status=pending` is the one the UI asks about."""
    output = await use_case.execute(
        ListChargesInputDTO(user_id=caller.user_id, status=status_filter)
    )
    return ChargesListResponse(**output.model_dump())


@router.post("/{charge_id}/confirm", response_model=ChargeResponse)
async def confirm_charge(
    charge_id: str,
    body: ConfirmChargeRequest | None = None,
    caller: CallerContext = Depends(get_caller),
    use_case: ConfirmChargeUseCase = Depends(_depends_confirm_use_case),
) -> ChargeResponse:
    """Registers the expense the subscription was waiting on.

    Send `amount` when the real charge differs from the expected one (a price rise):
    the movement records what actually happened. Confirming twice answers
    `subscriptions.charge_already_settled` instead of charging again.
    """
    output = await use_case.execute(
        SettleChargeInputDTO(
            user_id=caller.user_id,
            charge_id=charge_id,
            amount=body.amount if body is not None else None,
        )
    )
    return ChargeResponse(**output.model_dump())


@router.post("/{charge_id}/skip", response_model=ChargeResponse)
async def skip_charge(
    charge_id: str,
    caller: CallerContext = Depends(get_caller),
    use_case: SkipChargeUseCase = Depends(_depends_skip_use_case),
) -> ChargeResponse:
    """It did not happen: no movement, and the confirmation window stops running."""
    output = await use_case.execute(
        SettleChargeInputDTO(user_id=caller.user_id, charge_id=charge_id)
    )
    return ChargeResponse(**output.model_dump())
