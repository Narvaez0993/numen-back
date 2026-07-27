from dataclasses import dataclass

from src.modules.subscriptions.application.dto.charge import ChargeDTO, SettleChargeInputDTO
from src.modules.subscriptions.application.ports.charge_repository import ChargeRepository
from src.modules.subscriptions.application.services.charge_settlement import ChargeSettlement
from src.modules.subscriptions.domain.errors import (
    ChargeAlreadySettledError,
    ChargeNotFoundError,
)


@dataclass
class SkipChargeUseCase:
    """The user says it did not happen: no movement, and the window stops running.

    This is the escape hatch that makes the automatic settlement acceptable — a
    cancelled service, a refund or a declined card can be dismissed instead of
    landing in the ledger.
    """

    charge_repository: ChargeRepository
    settlement: ChargeSettlement

    async def execute(self, input_dto: SettleChargeInputDTO) -> ChargeDTO:
        charge = await self.charge_repository.find(input_dto.user_id, input_dto.charge_id)
        if charge is None:
            raise ChargeNotFoundError()
        if charge.is_settled:
            raise ChargeAlreadySettledError()

        return ChargeDTO.from_domain(await self.settlement.skip(charge))
