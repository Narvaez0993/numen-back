from dataclasses import dataclass

from src.modules.debts.application.dto.debt_commands import DeleteDebtInputDTO
from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.debts.application.ports.event_repository import EventRepository
from src.modules.debts.application.ports.settlement_reader import (
    NO_SETTLEMENT,
    SettlementReader,
)
from src.modules.debts.application.ports.transfer_recorder import TransferRecorder
from src.modules.debts.domain.errors import DebtNotFoundError


@dataclass
class DeleteDebtUseCase:
    """Forgets a debt, and gives back every peso it moved.

    Deleting is "this never happened", so the cash has to agree: the loan, each
    repayment and the write-off were real movements, and leaving them behind would
    strand them against a debt that no longer exists — an account short a hundred
    thousand pesos with nothing on screen to explain why.

    The debt's own record is what disappears; the movements are reverted through the
    same port that made them, so the accounts land exactly where they started.

    If it was the last debt of a shared event, the event goes with it: an event is
    only the grouping of its debts, and an empty group is not a thing the screen
    should ever have to render.
    """

    debt_repository: DebtRepository
    event_repository: EventRepository
    settlement_reader: SettlementReader
    transfer_recorder: TransferRecorder

    async def execute(self, input_dto: DeleteDebtInputDTO) -> None:
        debt = await self.debt_repository.find(input_dto.user_id, input_dto.debt_id)
        if debt is None:
            raise DebtNotFoundError()

        settlements = await self.settlement_reader.settlements(input_dto.user_id)
        settlement = settlements.get(debt.id, NO_SETTLEMENT)
        for movement in settlement.into_debt + settlement.out_of_debt:
            await self.transfer_recorder.revert(
                user_id=input_dto.user_id, movement_id=movement.movement_id
            )

        await self.debt_repository.delete(input_dto.user_id, input_dto.debt_id)

        if debt.event_id is not None:
            siblings = await self.debt_repository.list_by_event(input_dto.user_id, debt.event_id)
            if not siblings:
                await self.event_repository.delete(input_dto.user_id, debt.event_id)
