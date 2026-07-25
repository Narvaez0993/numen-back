from typing import Any
from uuid import UUID

from src.modules.movements.application.dto.movement_commands import CreateMovementInputDTO

from .fakes import CURRENCY, TODAY


def create_input(user_id: UUID, **overrides: Any) -> CreateMovementInputDTO:
    """A valid expense from an account, with anything overridden per test."""
    payload: dict[str, Any] = {
        "user_id": user_id,
        "currency": CURRENCY,
        "type": "expense",
        "description": "Café",
        "amount": 12_000,
        "source_type": "account",
        "source_id": "nequi",
        "category_id": "cafe",
        "occurred_on": TODAY,
    }
    payload.update(overrides)
    return CreateMovementInputDTO(**payload)
