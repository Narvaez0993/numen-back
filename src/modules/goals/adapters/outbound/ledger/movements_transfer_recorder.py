from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from src.modules.goals.application.ports.transfer_recorder import RecordedTransfer
from src.modules.movements.application.dto.movement_commands import CreateMovementInputDTO
from src.modules.movements.application.use_cases.create_movement import CreateMovementUseCase


@dataclass
class MovementsTransferRecorder:
    """`TransferRecorder` backed by the movements module.

    The anti-corruption seam, and the reason pocket money is real money: the transfer
    goes through the same use case as any movement, so it inherits the cash-basis
    deltas (the account's balance really moves), the atomicity, and the validations
    (the account exists, is the caller's, shares the currency). The goal endpoint is
    the ref HTTP cannot mint — only this port does.
    """

    create_movement: CreateMovementUseCase

    async def record(
        self,
        *,
        user_id: UUID,
        currency: str,
        description: str,
        amount: int,
        account_id: str,
        goal_id: str,
        direction: Literal["in", "out"],
        occurred_on: str,
    ) -> RecordedTransfer:
        into_pocket = direction == "in"
        output = await self.create_movement.execute(
            CreateMovementInputDTO(
                user_id=user_id,
                currency=currency,
                type="transfer",
                description=description,
                amount=amount,
                source_type="account" if into_pocket else "goal",
                source_id=account_id if into_pocket else goal_id,
                destination_type="goal" if into_pocket else "account",
                destination_id=goal_id if into_pocket else account_id,
                occurred_on=occurred_on,
            )
        )
        return RecordedTransfer(movement_id=output.id)
