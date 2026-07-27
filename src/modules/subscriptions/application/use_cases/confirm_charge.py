from dataclasses import dataclass

from src.modules.subscriptions.application.dto.charge import ChargeDTO, SettleChargeInputDTO
from src.modules.subscriptions.application.ports.charge_repository import ChargeRepository
from src.modules.subscriptions.application.services.charge_settlement import ChargeSettlement
from src.modules.subscriptions.domain.errors import (
    ChargeAlreadySettledError,
    ChargeNotFoundError,
)


@dataclass
class ConfirmChargeUseCase:
    """The user says "yes, they charged me" — one tap becomes a real expense."""

    charge_repository: ChargeRepository
    settlement: ChargeSettlement

    async def execute(self, input_dto: SettleChargeInputDTO) -> ChargeDTO:
        charge = await self.charge_repository.find(input_dto.user_id, input_dto.charge_id)
        if charge is None:
            raise ChargeNotFoundError()
        if charge.is_settled:
            # Either a double tap or the window closed a second ago: both mean the
            # movement already exists, and creating a second one would cost money.
            raise ChargeAlreadySettledError()

        settled = await self.settlement.settle(charge, status="confirmed", amount=input_dto.amount)
        return ChargeDTO.from_domain(settled)
