from dataclasses import dataclass

from src.modules.debts.application.dto.debt import AddPaymentOutputDTO, DebtDTO
from src.modules.debts.application.dto.debt_commands import AddPaymentInputDTO
from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.debts.application.ports.settlement_reader import (
    NO_SETTLEMENT,
    SettlementReader,
)
from src.modules.debts.application.ports.transfer_recorder import TransferRecorder
from src.modules.debts.application.services import settlement as settlement_service
from src.modules.debts.domain import status as debt_status
from src.modules.debts.domain.errors import (
    DebtNotFoundError,
    InvalidDebtError,
    OverpaidError,
)
from src.modules.debts.domain.validation import ensure_note


@dataclass
class AddPaymentUseCase:
    """A repayment: the money lands on an account and the debt shrinks, in one act.

    These are the same event, so they are the same record — a transfer between the
    debt and the account. Nothing is written onto the debt, because what has been
    repaid is read back from these transfers. Delete the movement in Movimientos and
    the account gives the money back *and* the debt reopens; there is no second copy
    left telling a different story.

    Which way the cash flows follows the direction: someone paying back what they owe
    me puts money **into** my account; me paying off what I owe takes it out.

    Overpaying is rejected, not clamped: a payment above what is owed is either a typo
    or a different agreement (a new debt the other way), and both deserve the user's
    attention rather than a silent `remaining: 0`.

    It answers with the debt AND the id of the movement that carried the money, because
    undoing a repayment means deleting exactly that movement — a caller that only got
    the debt back would have to guess which of its instalments was the new one.
    """

    debt_repository: DebtRepository
    settlement_reader: SettlementReader
    transfer_recorder: TransferRecorder

    async def execute(self, input_dto: AddPaymentInputDTO) -> AddPaymentOutputDTO:
        debt = await self.debt_repository.find(input_dto.user_id, input_dto.debt_id)
        if debt is None:
            raise DebtNotFoundError()

        if input_dto.amount <= 0:
            raise InvalidDebtError("A payment has to be a positive amount")
        if not input_dto.account_id:
            raise InvalidDebtError("A repayment has to name the account the money moves on")

        settlements = await self.settlement_reader.settlements(input_dto.user_id)
        before = settlements.get(debt.id, NO_SETTLEMENT)
        if input_dto.amount > debt_status.remaining(debt, settlement_service.repaid(debt, before)):
            raise OverpaidError()

        note = ensure_note(input_dto.note)
        recorded = await self.transfer_recorder.record(
            user_id=input_dto.user_id,
            currency=debt.currency,
            description=note or _DESCRIPTION[debt.direction],
            amount=input_dto.amount,
            account_id=input_dto.account_id,
            debt_id=debt.id,
            # `incoming` = they owe me, so their payment arrives on my account.
            direction="in" if debt.direction == "incoming" else "out",
            occurred_on=input_dto.today,
        )

        after = await self.settlement_reader.settlements(input_dto.user_id)
        return AddPaymentOutputDTO(
            debt=DebtDTO.from_domain(debt, after.get(debt.id, NO_SETTLEMENT), input_dto.today),
            movement_id=recorded.movement_id,
        )


#: A repayment with nothing written on it still needs a name in Movimientos.
_DESCRIPTION: dict[str, str] = {
    "incoming": "Abono recibido",
    "outgoing": "Abono pagado",
}
