from fastapi import APIRouter, Depends, Query, status

from src.modules.subscriptions.adapters.inbound.http.schemas import (
    CreateSubscriptionRequest,
    SubscriptionResponse,
    SubscriptionsOverviewResponse,
    UpdateSubscriptionRequest,
)
from src.modules.subscriptions.application.dto.subscription_commands import (
    CreateSubscriptionInputDTO,
    DeleteSubscriptionInputDTO,
    ListSubscriptionsInputDTO,
    UpdateSubscriptionInputDTO,
)
from src.modules.subscriptions.application.use_cases.create_subscription import (
    CreateSubscriptionUseCase,
)
from src.modules.subscriptions.application.use_cases.delete_subscription import (
    DeleteSubscriptionUseCase,
)
from src.modules.subscriptions.application.use_cases.list_subscriptions import (
    ListSubscriptionsUseCase,
)
from src.modules.subscriptions.application.use_cases.update_subscription import (
    UpdateSubscriptionUseCase,
)
from src.shared.adapters.inbound.http.dependencies import CallerContext, get_caller
from src.shared.adapters.inbound.http.today import resolve_today

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _depends_list_use_case() -> ListSubscriptionsUseCase:
    from src.core.di.container import get_container

    return get_container().list_subscriptions_use_case


def _depends_create_use_case() -> CreateSubscriptionUseCase:
    from src.core.di.container import get_container

    return get_container().create_subscription_use_case


def _depends_update_use_case() -> UpdateSubscriptionUseCase:
    from src.core.di.container import get_container

    return get_container().update_subscription_use_case


def _depends_delete_use_case() -> DeleteSubscriptionUseCase:
    from src.core.di.container import get_container

    return get_container().delete_subscription_use_case


@router.get("", response_model=SubscriptionsOverviewResponse)
async def list_subscriptions(
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: ListSubscriptionsUseCase = Depends(_depends_list_use_case),
) -> SubscriptionsOverviewResponse:
    """The subscriptions screen in one read: the list plus the normalised totals."""
    output = await use_case.execute(
        ListSubscriptionsInputDTO(
            user_id=caller.user_id,
            currency=caller.currency,
            today=resolve_today(today),
        )
    )
    return SubscriptionsOverviewResponse(**output.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SubscriptionResponse)
async def create_subscription(
    body: CreateSubscriptionRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: CreateSubscriptionUseCase = Depends(_depends_create_use_case),
) -> SubscriptionResponse:
    """Registers a recurring charge. Nothing is charged here — this is a forecast."""
    output = await use_case.execute(
        CreateSubscriptionInputDTO(
            user_id=caller.user_id,
            currency=caller.currency,
            today=resolve_today(today),
            name=body.name,
            amount=body.amount,
            frequency=body.frequency,
            first_charge_on=body.first_charge_on,
            source_type=body.source_type,
            source_id=body.source_id,
            category_id=body.category_id,
            icon=body.icon,
            color=body.color,
        )
    )
    return SubscriptionResponse(**output.model_dump())


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: str,
    body: UpdateSubscriptionRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: UpdateSubscriptionUseCase = Depends(_depends_update_use_case),
) -> SubscriptionResponse:
    """Patches it. Charges already opened keep the amount they froze."""
    output = await use_case.execute(
        UpdateSubscriptionInputDTO(
            user_id=caller.user_id,
            currency=caller.currency,
            today=resolve_today(today),
            subscription_id=subscription_id,
            name=body.name,
            amount=body.amount,
            frequency=body.frequency,
            first_charge_on=body.first_charge_on,
            source_type=body.source_type,
            source_id=body.source_id,
            category_id=body.category_id,
            icon=body.icon,
            color=body.color,
            active=body.active,
        )
    )
    return SubscriptionResponse(**output.model_dump())


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: str,
    caller: CallerContext = Depends(get_caller),
    use_case: DeleteSubscriptionUseCase = Depends(_depends_delete_use_case),
) -> None:
    """Forgets the subscription; the movements it produced stay — they were real."""
    await use_case.execute(
        DeleteSubscriptionInputDTO(
            user_id=caller.user_id,
            subscription_id=subscription_id,
        )
    )
