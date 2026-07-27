from dataclasses import dataclass
from uuid import UUID

from src.modules.movements.application.dto.movement_commands import CreateMovementInputDTO
from src.modules.movements.application.use_cases.create_movement import CreateMovementUseCase
from src.modules.subscriptions.application.ports.expense_recorder import RecordedExpense
from src.modules.subscriptions.domain.entities.subscription import SourceRef


@dataclass
class MovementsExpenseRecorder:
    """`ExpenseRecorder` backed by the movements module.

    The anti-corruption seam: it talks to a **use case**, never to the movements
    collection, so the charge inherits everything that flow already guarantees —
    cash-basis (a card charge raises its debt), atomicity, and the idempotency key
    that makes a retried settlement return the original movement.

    `captured_via="recurring"` is the audit trail: this expense was not typed by the
    user, and the row can say so.
    """

    create_movement: CreateMovementUseCase

    async def record(
        self,
        *,
        user_id: UUID,
        currency: str,
        description: str,
        amount: int,
        source: SourceRef,
        category_id: str | None,
        occurred_on: str,
        subscription_id: str,
        idempotency_key: str,
    ) -> RecordedExpense:
        output = await self.create_movement.execute(
            CreateMovementInputDTO(
                user_id=user_id,
                currency=currency,
                type="expense",
                description=description,
                amount=amount,
                source_type=source.type,
                source_id=source.id,
                category_id=category_id,
                occurred_on=occurred_on,
                captured_via="recurring",
                idempotency_key=idempotency_key,
                subscription_id=subscription_id,
            )
        )
        return RecordedExpense(movement_id=output.id)
