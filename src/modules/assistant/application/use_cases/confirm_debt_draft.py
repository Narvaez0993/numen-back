"""Confirming a debt draft — either opening a debt or paying one down.

Both go through the use case the manual flow uses, so the person is resolved (or
created) once and the transfer moves the account's balance for real.

The two differ in what they can leave blank. A NEW debt can legitimately confirm with
no account: a dinner split moves no cash, because the bill already left as one expense.
A PAYMENT cannot — money always changes hands when a debt is paid down, and "no money
moved" is not an answer to it, it is a contradiction.
"""

from dataclasses import dataclass

from src.modules.assistant.application.dto.debt_draft import DebtDraftDTO
from src.modules.assistant.application.dto.debt_draft_commands import (
    ConfirmDebtDraftInputDTO,
    ConfirmDebtDraftOutputDTO,
)
from src.modules.assistant.application.ports.debt_draft_repository import DebtDraftRepository
from src.modules.assistant.application.ports.debt_payment_recorder import (
    DebtPaymentRecorder,
)
from src.modules.assistant.application.ports.debt_recorder import DebtRecorder
from src.modules.assistant.domain.entities.debt_draft import DebtDraft
from src.modules.assistant.domain.errors import (
    DebtPaymentAccountRequiredError,
    DebtPaymentTargetRequiredError,
    DraftNotFoundError,
)

_OVERRIDABLE = (
    "target_debt_id",
    "direction",
    "counterparty_id",
    "counterparty_name",
    "amount",
    "due_on",
    "note",
)


@dataclass
class ConfirmDebtDraftUseCase:
    debt_drafts: DebtDraftRepository
    debt_recorder: DebtRecorder
    payment_recorder: DebtPaymentRecorder

    async def execute(self, input_dto: ConfirmDebtDraftInputDTO) -> ConfirmDebtDraftOutputDTO:
        draft = await self.debt_drafts.find(input_dto.user_id, input_dto.draft_id)
        if draft is None:
            raise DraftNotFoundError()

        edited = draft.apply_overrides(_overrides_from(input_dto))
        if edited.is_payment:
            return await self._pay(edited, input_dto.today)

        recorded = await self.debt_recorder.record(
            user_id=edited.user_id,
            currency=edited.currency,
            today=input_dto.today,
            direction=edited.direction,
            counterparty_id=edited.counterparty_id,
            # The id wins when there is one: naming an existing person again would
            # create a second "Andrés" and split their debts across both.
            counterparty_name=None if edited.counterparty_id else edited.counterparty_name,
            amount=edited.amount,
            account_id=edited.account_id,
            due_on=edited.due_on,
            note=edited.note,
        )
        confirmed = edited.confirm(recorded.debt_id)
        await self.debt_drafts.save(confirmed)
        return ConfirmDebtDraftOutputDTO(
            draft=DebtDraftDTO.from_domain(confirmed), debt_id=recorded.debt_id
        )

    async def _pay(self, draft: DebtDraft, today: str) -> ConfirmDebtDraftOutputDTO:
        """An abono. The debt already exists, so nothing is created — the transfer
        that carries the money is the whole record, and what has been repaid is read
        back from it."""
        if draft.target_debt_id is None:
            # The capture named nobody and the card was supposed to ask. Reaching
            # here means it confirmed around the question — paying down nothing at
            # all while reporting success.
            raise DebtPaymentTargetRequiredError()
        if not draft.account_id:
            raise DebtPaymentAccountRequiredError()

        recorded = await self.payment_recorder.record(
            user_id=draft.user_id,
            today=today,
            debt_id=draft.target_debt_id,
            amount=draft.amount,
            account_id=draft.account_id,
            note=draft.note,
        )
        confirmed = draft.confirm(draft.target_debt_id)
        await self.debt_drafts.save(confirmed)
        return ConfirmDebtDraftOutputDTO(
            draft=DebtDraftDTO.from_domain(confirmed),
            debt_id=draft.target_debt_id,
            movement_id=recorded.movement_id,
        )


def _overrides_from(input_dto: ConfirmDebtDraftInputDTO) -> dict[str, object]:
    overrides: dict[str, object] = {
        name: value for name in _OVERRIDABLE if (value := getattr(input_dto, name)) is not None
    }
    if input_dto.clear_account:
        overrides["account_id"] = None
    elif input_dto.account_id is not None:
        overrides["account_id"] = input_dto.account_id
    return overrides
