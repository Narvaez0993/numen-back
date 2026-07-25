from dataclasses import dataclass

from src.modules.movements.application.dto.movement_commands import DeleteMovementInputDTO
from src.modules.movements.application.ports.movement_repository import MovementRepository
from src.modules.movements.application.ports.source_ledger import SourceLedger
from src.modules.movements.domain.errors import MovementNotFoundError
from src.shared.application.ports.unit_of_work import UnitOfWork


@dataclass
class DeleteMovementUseCase:
    """Removes a movement and gives back the money it had moved.

    Same transaction, so the ledger never keeps an effect whose cause is gone.
    This is also what makes "undo" real on the client.
    """

    movement_repository: MovementRepository
    source_ledger: SourceLedger
    unit_of_work: UnitOfWork

    async def execute(self, input_dto: DeleteMovementInputDTO) -> None:
        current = await self.movement_repository.find(input_dto.user_id, input_dto.movement_id)
        if current is None:
            raise MovementNotFoundError()

        async def apply() -> None:
            for ref, delta in current.reverted_deltas():
                await self.source_ledger.apply_delta(input_dto.user_id, ref, delta)
            await self.movement_repository.delete(input_dto.user_id, input_dto.movement_id)

        await self.unit_of_work.atomic(apply)
