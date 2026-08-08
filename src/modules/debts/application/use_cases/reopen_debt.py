from dataclasses import dataclass

from src.modules.debts.application.dto.debt import DebtDTO
from src.modules.debts.application.dto.debt_commands import ReopenDebtInputDTO
from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.debts.application.ports.settlement_reader import (
    NO_SETTLEMENT,
    SettlementReader,
)
from src.modules.debts.application.ports.transfer_recorder import TransferRecorder
from src.modules.debts.application.services import settlement as settlement_service
from src.modules.debts.domain.errors import DebtNotFoundError, NotWrittenOffError


@dataclass
class ReopenDebtUseCase:
    """They paid after all. Undoes a write-off, loss and all.

    Deleting the expense is what makes it a true undo rather than a correction: the
    month it was written off stops showing a loss that never happened, and the claim
    comes back at exactly the amount it stood at. Nothing has to be recomputed,
    because nothing was ever stored — the loss WAS that movement.

    It exists because writing off is a judgement call made under uncertainty ("I do
    not think Andrés is paying"), and a judgement the user cannot take back is one
    they will hesitate to make at all.
    """

    debt_repository: DebtRepository
    settlement_reader: SettlementReader
    transfer_recorder: TransferRecorder

    async def execute(self, input_dto: ReopenDebtInputDTO) -> DebtDTO:
        debt = await self.debt_repository.find(input_dto.user_id, input_dto.debt_id)
        if debt is None:
            raise DebtNotFoundError()
        if debt.written_off_on is None:
            raise NotWrittenOffError()

        settlements = await self.settlement_reader.settlements(input_dto.user_id)
        for loss in settlement_service.losses(settlements.get(debt.id, NO_SETTLEMENT)):
            await self.transfer_recorder.revert(
                user_id=input_dto.user_id, movement_id=loss.movement_id
            )

        alive = debt.with_changes(written_off_on=None)
        await self.debt_repository.save(alive)

        after = await self.settlement_reader.settlements(input_dto.user_id)
        return DebtDTO.from_domain(alive, after.get(debt.id, NO_SETTLEMENT), input_dto.today)
