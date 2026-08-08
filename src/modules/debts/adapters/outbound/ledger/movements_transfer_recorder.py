from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from src.modules.debts.application.ports.transfer_recorder import RecordedTransfer
from src.modules.movements.application.dto.movement_commands import (
    CreateMovementInputDTO,
    DeleteMovementInputDTO,
)
from src.modules.movements.application.use_cases.create_movement import CreateMovementUseCase
from src.modules.movements.application.use_cases.delete_movement import DeleteMovementUseCase


@dataclass
class MovementsTransferRecorder:
    """`TransferRecorder` backed by the movements module.

    The anti-corruption seam, and the reason lending finally tells the truth: the
    transfer goes through the same use case as any movement, so it inherits the
    cash-basis deltas (the account's balance really moves), the atomicity, and the
    validations (the account exists, is the caller's, shares the currency). And
    because a transfer counts toward neither expenses nor income, handing a friend
    money stops looking like spending it.

    The `debt` endpoint is the ref HTTP cannot mint — only this port does.
    """

    create_movement: CreateMovementUseCase
    delete_movement: DeleteMovementUseCase

    async def record(
        self,
        *,
        user_id: UUID,
        currency: str,
        description: str,
        amount: int,
        account_id: str,
        debt_id: str,
        direction: Literal["out", "in"],
        occurred_on: str,
    ) -> RecordedTransfer:
        into_debt = direction == "out"
        output = await self.create_movement.execute(
            CreateMovementInputDTO(
                user_id=user_id,
                currency=currency,
                type="transfer",
                description=description,
                amount=amount,
                source_type="account" if into_debt else "debt",
                source_id=account_id if into_debt else debt_id,
                destination_type="debt" if into_debt else "account",
                destination_id=debt_id if into_debt else account_id,
                occurred_on=occurred_on,
            )
        )
        return RecordedTransfer(movement_id=output.id)

    async def record_loss(
        self,
        *,
        user_id: UUID,
        currency: str,
        description: str,
        amount: int,
        debt_id: str,
        occurred_on: str,
    ) -> RecordedTransfer:
        """An expense whose source is the debt — the shape `validation.py` allows for
        exactly this, and which no HTTP request can ask for.

        No category: the loss belongs to no spending habit, and forcing one would put
        a friend who never paid inside "Comida" for the rest of the year.
        """
        output = await self.create_movement.execute(
            CreateMovementInputDTO(
                user_id=user_id,
                currency=currency,
                type="expense",
                description=description,
                amount=amount,
                source_type="debt",
                source_id=debt_id,
                occurred_on=occurred_on,
            )
        )
        return RecordedTransfer(movement_id=output.id)

    async def revert(self, *, user_id: UUID, movement_id: str) -> bool:
        """Deleting the movement is the whole undo: the account's balance comes back
        by the same delta rule that moved it, and — since a debt's progress is read
        from these transfers — the debt reopens with it, with nothing to reconcile.

        Movements raises when the id is not the caller's, so reaching the return
        means it is gone."""
        await self.delete_movement.execute(
            DeleteMovementInputDTO(user_id=user_id, movement_id=movement_id)
        )
        return True
