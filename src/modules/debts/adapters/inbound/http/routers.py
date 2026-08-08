from fastapi import APIRouter, Depends, Query, status

from src.modules.debts.adapters.inbound.http.schemas import (
    AddPaymentRequest,
    CreateDebtRequest,
    CreateSharedEventRequest,
    DebtResponse,
    DebtsSnapshotResponse,
    UpdateDebtRequest,
)
from src.modules.debts.application.dto.debt_commands import (
    AddPaymentInputDTO,
    CreateDebtInputDTO,
    CreateSharedEventInputDTO,
    DebtsSnapshotInputDTO,
    DeleteDebtInputDTO,
    RemovePaymentInputDTO,
    ReopenDebtInputDTO,
    SplitInputDTO,
    UpdateDebtInputDTO,
    WriteOffDebtInputDTO,
)
from src.modules.debts.application.use_cases.add_payment import AddPaymentUseCase
from src.modules.debts.application.use_cases.create_debt import CreateDebtUseCase
from src.modules.debts.application.use_cases.create_shared_event import (
    CreateSharedEventUseCase,
)
from src.modules.debts.application.use_cases.delete_debt import DeleteDebtUseCase
from src.modules.debts.application.use_cases.get_debts_snapshot import (
    GetDebtsSnapshotUseCase,
)
from src.modules.debts.application.use_cases.remove_payment import RemovePaymentUseCase
from src.modules.debts.application.use_cases.reopen_debt import ReopenDebtUseCase
from src.modules.debts.application.use_cases.update_debt import UpdateDebtUseCase
from src.modules.debts.application.use_cases.write_off_debt import WriteOffDebtUseCase
from src.shared.adapters.inbound.http.dependencies import CallerContext, get_caller
from src.shared.adapters.inbound.http.today import resolve_today

router = APIRouter(prefix="/debts", tags=["debts"])


def _depends_snapshot() -> GetDebtsSnapshotUseCase:
    from src.core.di.container import get_container

    return get_container().get_debts_snapshot_use_case


def _depends_create() -> CreateDebtUseCase:
    from src.core.di.container import get_container

    return get_container().create_debt_use_case


def _depends_create_event() -> CreateSharedEventUseCase:
    from src.core.di.container import get_container

    return get_container().create_shared_event_use_case


def _depends_update() -> UpdateDebtUseCase:
    from src.core.di.container import get_container

    return get_container().update_debt_use_case


def _depends_write_off() -> WriteOffDebtUseCase:
    from src.core.di.container import get_container

    return get_container().write_off_debt_use_case


def _depends_reopen() -> ReopenDebtUseCase:
    from src.core.di.container import get_container

    return get_container().reopen_debt_use_case


def _depends_delete() -> DeleteDebtUseCase:
    from src.core.di.container import get_container

    return get_container().delete_debt_use_case


def _depends_add_payment() -> AddPaymentUseCase:
    from src.core.di.container import get_container

    return get_container().add_payment_use_case


def _depends_remove_payment() -> RemovePaymentUseCase:
    from src.core.di.container import get_container

    return get_container().remove_payment_use_case


@router.get("/snapshot", response_model=DebtsSnapshotResponse)
async def get_snapshot(
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: GetDebtsSnapshotUseCase = Depends(_depends_snapshot),
) -> DebtsSnapshotResponse:
    """The Deudas screen in one read. `today` is the caller's local day — `status`
    and therefore `overdue` are derived from it, never stored."""
    output = await use_case.execute(
        DebtsSnapshotInputDTO(
            user_id=caller.user_id,
            currency=caller.currency,
            today=resolve_today(today),
        )
    )
    return DebtsSnapshotResponse(**output.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DebtResponse)
async def create_debt(
    body: CreateDebtRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: CreateDebtUseCase = Depends(_depends_create),
) -> DebtResponse:
    """A one-on-one debt. It records who owes whom — no movement, no balance: the
    ledger is parallel to the money on purpose."""
    output = await use_case.execute(
        CreateDebtInputDTO(
            user_id=caller.user_id,
            currency=caller.currency,
            today=resolve_today(today),
            direction=body.direction,
            counterparty_id=body.counterparty_id,
            counterparty_name=body.counterparty_name,
            amount=body.amount,
            account_id=body.account_id,
            due_on=body.due_on,
            note=body.note,
        )
    )
    return DebtResponse(**output.model_dump())


@router.post("/events", status_code=status.HTTP_201_CREATED, response_model=DebtsSnapshotResponse)
async def create_shared_event(
    body: CreateSharedEventRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: CreateSharedEventUseCase = Depends(_depends_create_event),
) -> DebtsSnapshotResponse:
    """The dinner, split: one event plus a debt per person, atomically. Answers with
    the whole snapshot — the screen redraws everything after a split anyway."""
    output = await use_case.execute(
        CreateSharedEventInputDTO(
            user_id=caller.user_id,
            currency=caller.currency,
            today=resolve_today(today),
            direction=body.direction,
            name=body.name,
            total=body.total,
            due_on=body.due_on,
            splits=[
                SplitInputDTO(
                    counterparty_id=split.counterparty_id,
                    counterparty_name=split.counterparty_name,
                    amount=split.amount,
                )
                for split in body.splits
            ],
        )
    )
    return DebtsSnapshotResponse(**output.model_dump())


@router.patch("/{debt_id}", response_model=DebtResponse)
async def update_debt(
    debt_id: str,
    body: UpdateDebtRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: UpdateDebtUseCase = Depends(_depends_update),
) -> DebtResponse:
    """Patches what the debt says (amount, due date, note) — never who it is between.
    `due_on`/`note` sent explicitly as `null` clear the field."""
    fields = body.model_fields_set
    output = await use_case.execute(
        UpdateDebtInputDTO(
            user_id=caller.user_id,
            debt_id=debt_id,
            today=resolve_today(today),
            amount=body.amount,
            due_on=body.due_on,
            clear_due_on="due_on" in fields and body.due_on is None,
            note=body.note,
            clear_note="note" in fields and body.note is None,
        )
    )
    return DebtResponse(**output.model_dump())


@router.delete("/{debt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_debt(
    debt_id: str,
    caller: CallerContext = Depends(get_caller),
    use_case: DeleteDebtUseCase = Depends(_depends_delete),
) -> None:
    """Forgets the debt; if it was the last one of an event, the event goes too."""
    await use_case.execute(DeleteDebtInputDTO(user_id=caller.user_id, debt_id=debt_id))


@router.post("/{debt_id}/payments", response_model=DebtResponse)
async def add_payment(
    debt_id: str,
    body: AddPaymentRequest,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: AddPaymentUseCase = Depends(_depends_add_payment),
) -> DebtResponse:
    """A partial repayment. More than what is owed → `debts.overpaid`, not a clamp."""
    output = await use_case.execute(
        AddPaymentInputDTO(
            user_id=caller.user_id,
            debt_id=debt_id,
            today=resolve_today(today),
            amount=body.amount,
            account_id=body.account_id,
            note=body.note,
        )
    )
    # The screen redraws from the debt; the movement id is for callers that undo.
    return DebtResponse(**output.debt.model_dump())


@router.delete("/{debt_id}/payments/{payment_id}", response_model=DebtResponse)
async def remove_payment(
    debt_id: str,
    payment_id: str,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: RemovePaymentUseCase = Depends(_depends_remove_payment),
) -> DebtResponse:
    """Undo for a mistyped payment — it can only raise what is owed."""
    output = await use_case.execute(
        RemovePaymentInputDTO(
            user_id=caller.user_id,
            debt_id=debt_id,
            payment_id=payment_id,
            today=resolve_today(today),
        )
    )
    return DebtResponse(**output.model_dump())


@router.post("/{debt_id}/write-off", response_model=DebtResponse)
async def write_off_debt(
    debt_id: str,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: WriteOffDebtUseCase = Depends(_depends_write_off),
) -> DebtResponse:
    """Gives up on money owed to the user, booking the loss as an expense today.

    Only for `incoming` debts → otherwise `debts.not_writable_off`. No body: the only
    input is the decision, and how much it costs is the ledger's to work out.
    """
    output = await use_case.execute(
        WriteOffDebtInputDTO(user_id=caller.user_id, debt_id=debt_id, today=resolve_today(today))
    )
    return DebtResponse(**output.model_dump())


@router.delete("/{debt_id}/write-off", response_model=DebtResponse)
async def reopen_debt(
    debt_id: str,
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: ReopenDebtUseCase = Depends(_depends_reopen),
) -> DebtResponse:
    """They paid after all: the claim comes back and the loss expense is deleted."""
    output = await use_case.execute(
        ReopenDebtInputDTO(user_id=caller.user_id, debt_id=debt_id, today=resolve_today(today))
    )
    return DebtResponse(**output.model_dump())
