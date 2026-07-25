from pydantic import BaseModel

from src.modules.movements.domain.entities.movement import Movement


class MovementDTO(BaseModel):
    """Transport shape of a movement. `amount` is positive; the sign lives in `type`."""

    id: str
    type: str
    description: str
    amount: int
    currency: str
    source_type: str
    source_id: str
    destination_type: str | None
    destination_id: str | None
    category_id: str | None
    occurred_on: str
    captured_via: str

    @classmethod
    def from_domain(cls, movement: Movement) -> "MovementDTO":
        return cls(
            id=movement.id,
            type=movement.type,
            description=movement.description,
            amount=movement.amount,
            currency=movement.currency,
            source_type=movement.source.type,
            source_id=movement.source.id,
            destination_type=(
                movement.destination.type if movement.destination is not None else None
            ),
            destination_id=(movement.destination.id if movement.destination is not None else None),
            category_id=movement.category_id,
            occurred_on=movement.occurred_on,
            captured_via=movement.captured_via,
        )
