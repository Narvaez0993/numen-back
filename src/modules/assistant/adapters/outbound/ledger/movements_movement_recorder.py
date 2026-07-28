from dataclasses import dataclass
from uuid import UUID

from src.modules.assistant.application.ports.movement_recorder import RecordedMovement
from src.modules.movements.application.dto.movement_commands import CreateMovementInputDTO
from src.modules.movements.application.use_cases.create_movement import CreateMovementUseCase


@dataclass
class MovementsMovementRecorder:
    """`MovementRecorder` backed by movements' create use case — the same door
    the manual form uses, so deltas, validation and idempotency stay one
    implementation. `captured_via="text"` says how this movement was born.
    """

    create_movement: CreateMovementUseCase

    async def record(
        self,
        *,
        user_id: UUID,
        currency: str,
        type: str,
        description: str,
        amount: int,
        source_type: str,
        source_id: str,
        destination_type: str | None,
        destination_id: str | None,
        category_id: str | None,
        occurred_on: str,
        idempotency_key: str,
    ) -> RecordedMovement:
        movement = await self.create_movement.execute(
            CreateMovementInputDTO(
                user_id=user_id,
                currency=currency,
                type=type,
                description=description,
                amount=amount,
                source_type=source_type,
                source_id=source_id,
                destination_type=destination_type,
                destination_id=destination_id,
                category_id=category_id,
                occurred_on=occurred_on,
                captured_via="text",
                idempotency_key=idempotency_key,
            )
        )
        return RecordedMovement(movement_id=movement.id)
