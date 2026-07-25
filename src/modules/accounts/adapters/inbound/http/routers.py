from fastapi import APIRouter, Depends, status

from src.modules.accounts.adapters.inbound.http.schemas import (
    AccountResponse,
    AccountsOverviewResponse,
    CreateAccountRequest,
    CreateCreditCardRequest,
    CreditCardResponse,
    UpdateAccountRequest,
    UpdateCreditCardRequest,
)
from src.modules.accounts.application.dto.account_commands import (
    CreateAccountInputDTO,
    DeleteAccountInputDTO,
    UpdateAccountInputDTO,
)
from src.modules.accounts.application.dto.accounts_overview import (
    AccountsOverviewInputDTO,
)
from src.modules.accounts.application.dto.credit_card_commands import (
    CreateCreditCardInputDTO,
    DeleteCreditCardInputDTO,
    UpdateCreditCardInputDTO,
)
from src.modules.accounts.application.use_cases.create_account import CreateAccountUseCase
from src.modules.accounts.application.use_cases.create_credit_card import (
    CreateCreditCardUseCase,
)
from src.modules.accounts.application.use_cases.delete_account import DeleteAccountUseCase
from src.modules.accounts.application.use_cases.delete_credit_card import (
    DeleteCreditCardUseCase,
)
from src.modules.accounts.application.use_cases.get_accounts_overview import (
    GetAccountsOverviewUseCase,
)
from src.modules.accounts.application.use_cases.update_account import UpdateAccountUseCase
from src.modules.accounts.application.use_cases.update_credit_card import (
    UpdateCreditCardUseCase,
)
from src.shared.adapters.inbound.http.dependencies import CallerContext, get_caller

router = APIRouter(prefix="/accounts", tags=["accounts"])
credit_cards_router = APIRouter(prefix="/credit-cards", tags=["accounts"])


def _depends_overview_use_case() -> GetAccountsOverviewUseCase:
    from src.core.di.container import get_container

    return get_container().get_accounts_overview_use_case


def _depends_create_account_use_case() -> CreateAccountUseCase:
    from src.core.di.container import get_container

    return get_container().create_account_use_case


def _depends_update_account_use_case() -> UpdateAccountUseCase:
    from src.core.di.container import get_container

    return get_container().update_account_use_case


def _depends_delete_account_use_case() -> DeleteAccountUseCase:
    from src.core.di.container import get_container

    return get_container().delete_account_use_case


def _depends_create_card_use_case() -> CreateCreditCardUseCase:
    from src.core.di.container import get_container

    return get_container().create_credit_card_use_case


def _depends_update_card_use_case() -> UpdateCreditCardUseCase:
    from src.core.di.container import get_container

    return get_container().update_credit_card_use_case


def _depends_delete_card_use_case() -> DeleteCreditCardUseCase:
    from src.core.di.container import get_container

    return get_container().delete_credit_card_use_case


@router.get("/overview", response_model=AccountsOverviewResponse)
async def accounts_overview(
    caller: CallerContext = Depends(get_caller),
    use_case: GetAccountsOverviewUseCase = Depends(_depends_overview_use_case),
) -> AccountsOverviewResponse:
    """The whole Accounts screen in one read: sources, cards and totals."""
    output = await use_case.execute(
        AccountsOverviewInputDTO(user_id=caller.user_id, currency=caller.currency)
    )
    return AccountsOverviewResponse(**output.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AccountResponse)
async def create_account(
    body: CreateAccountRequest,
    caller: CallerContext = Depends(get_caller),
    use_case: CreateAccountUseCase = Depends(_depends_create_account_use_case),
) -> AccountResponse:
    output = await use_case.execute(
        CreateAccountInputDTO(
            user_id=caller.user_id,
            tier=caller.tier,
            currency=caller.currency,
            kind=body.kind,
            name=body.name,
            sub=body.sub,
            icon=body.icon,
            color=body.color,
            balance=body.balance,
        )
    )
    return AccountResponse(**output.model_dump())


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str,
    body: UpdateAccountRequest,
    caller: CallerContext = Depends(get_caller),
    use_case: UpdateAccountUseCase = Depends(_depends_update_account_use_case),
) -> AccountResponse:
    output = await use_case.execute(
        UpdateAccountInputDTO(
            user_id=caller.user_id,
            account_id=account_id,
            name=body.name,
            sub=body.sub,
            icon=body.icon,
            color=body.color,
            balance=body.balance,
        )
    )
    return AccountResponse(**output.model_dump())


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    caller: CallerContext = Depends(get_caller),
    use_case: DeleteAccountUseCase = Depends(_depends_delete_account_use_case),
) -> None:
    await use_case.execute(DeleteAccountInputDTO(user_id=caller.user_id, account_id=account_id))


@credit_cards_router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=CreditCardResponse
)
async def create_credit_card(
    body: CreateCreditCardRequest,
    caller: CallerContext = Depends(get_caller),
    use_case: CreateCreditCardUseCase = Depends(_depends_create_card_use_case),
) -> CreditCardResponse:
    output = await use_case.execute(
        CreateCreditCardInputDTO(
            user_id=caller.user_id,
            tier=caller.tier,
            currency=caller.currency,
            name=body.name,
            icon=body.icon,
            color=body.color,
            debt=body.debt,
            limit=body.limit,
            cutoff_day=body.cutoff_day,
            due_day=body.due_day,
        )
    )
    return CreditCardResponse(**output.model_dump())


@credit_cards_router.patch("/{card_id}", response_model=CreditCardResponse)
async def update_credit_card(
    card_id: str,
    body: UpdateCreditCardRequest,
    caller: CallerContext = Depends(get_caller),
    use_case: UpdateCreditCardUseCase = Depends(_depends_update_card_use_case),
) -> CreditCardResponse:
    output = await use_case.execute(
        UpdateCreditCardInputDTO(
            user_id=caller.user_id,
            card_id=card_id,
            name=body.name,
            icon=body.icon,
            color=body.color,
            debt=body.debt,
            limit=body.limit,
            cutoff_day=body.cutoff_day,
            due_day=body.due_day,
        )
    )
    return CreditCardResponse(**output.model_dump())


@credit_cards_router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credit_card(
    card_id: str,
    caller: CallerContext = Depends(get_caller),
    use_case: DeleteCreditCardUseCase = Depends(_depends_delete_card_use_case),
) -> None:
    await use_case.execute(DeleteCreditCardInputDTO(user_id=caller.user_id, card_id=card_id))
