from dataclasses import dataclass

from src.modules.debts.application.dto.debt import DebtDTO
from src.modules.debts.application.dto.debt_commands import RemovePaymentInputDTO
from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.debts.application.ports.settlement_reader import (
    NO_SETTLEMENT,
    SettlementReader,
)
from src.modules.debts.application.ports.transfer_recorder import TransferRecorder
from src.modules.debts.application.services import settlement as settlement_service
from src.modules.debts.domain.errors import DebtNotFoundError, InvalidDebtError


@dataclass
class RemovePaymentUseCase:
    """Undo for a mistyped repayment — the same courtesy movements give with delete.

    A repayment is its transfer, so undoing it is deleting that movement: the account
    gives the money back and the debt reopens, from one act. Nothing is written on the
    debt here, because nothing about the repayment was ever written there.

    Removing it can only ever *raise* what is owed, so there is no overpay-style check
    to mirror here.
    """

    debt_repository: DebtRepository
    settlement_reader: SettlementReader
    transfer_recorder: TransferRecorder

    async def execute(self, input_dto: RemovePaymentInputDTO) -> DebtDTO:
        debt = await self.debt_repository.find(input_dto.user_id, input_dto.debt_id)
        if debt is None:
            raise DebtNotFoundError()

        settlements = await self.settlement_reader.settlements(input_dto.user_id)
        before = settlements.get(debt.id, NO_SETTLEMENT)
        # Check it belongs to THIS debt: the id is a movement's, and deleting a
        # movement that happens to exist elsewhere would be someone else's undo.
        paid = settlement_service.instalments(debt, before)
        if all(r.movement_id != input_dto.payment_id for r in paid):
            raise InvalidDebtError("That payment does not exist")

        await self.transfer_recorder.revert(
            user_id=input_dto.user_id, movement_id=input_dto.payment_id
        )

        after = await self.settlement_reader.settlements(input_dto.user_id)
        return DebtDTO.from_domain(debt, after.get(debt.id, NO_SETTLEMENT), input_dto.today)
