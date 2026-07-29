"""Outbound port: turning a confirmed draft into a real movement.

The adapter calls movements' `CreateMovementUseCase` — the same door the manual
form uses, so deltas, idempotency and validation are one implementation. The
draft id doubles as the idempotency key: a double-tapped confirm converges on a
single movement. `captured_via` travels from the draft — the movement remembers
whether it was spoken or typed.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class RecordedMovement:
    movement_id: str


class MovementRecorder(Protocol):
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
        captured_via: str,
        idempotency_key: str,
    ) -> RecordedMovement: ...
