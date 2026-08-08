from dataclasses import dataclass

from src.modules.movements.application.dto.debt_transfers import (
    DebtTransferDTO,
    DebtTransfersInputDTO,
    DebtTransfersOutputDTO,
)
from src.modules.movements.application.ports.movement_repository import MovementRepository


@dataclass
class GetDebtTransfersUseCase:
    """The cash that crossed between accounts and debts — the transfers themselves.

    The building block the debts module reads through its port. It lives here because
    those transfers are this module's rows: a debt has no stored progress to ask, and
    that is the point — what has been repaid cannot drift from the movements that
    repaid it.
    """

    movement_repository: MovementRepository

    async def execute(self, input_dto: DebtTransfersInputDTO) -> DebtTransfersOutputDTO:
        transfers = await self.movement_repository.debt_transfers(input_dto.user_id)
        return DebtTransfersOutputDTO(
            transfers=[DebtTransferDTO.from_domain(row) for row in transfers]
        )
