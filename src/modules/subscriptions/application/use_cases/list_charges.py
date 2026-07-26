from dataclasses import dataclass

from src.modules.subscriptions.application.dto.charge import (
    ChargeDTO,
    ChargesListDTO,
    ListChargesInputDTO,
)
from src.modules.subscriptions.application.ports.charge_repository import ChargeRepository


@dataclass
class ListChargesUseCase:
    charge_repository: ChargeRepository

    async def execute(self, input_dto: ListChargesInputDTO) -> ChargesListDTO:
        charges = await self.charge_repository.list_by_status(input_dto.user_id, input_dto.status)
        # Oldest due first: the one that has been waiting longest is the one to answer.
        charges.sort(key=lambda c: c.due_on)
        return ChargesListDTO(charges=[ChargeDTO.from_domain(c) for c in charges])
