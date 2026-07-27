from uuid import UUID

from pydantic import BaseModel

from src.modules.subscriptions.domain.entities.subscription_charge import SubscriptionCharge


class ChargeDTO(BaseModel):
    """A charge as the client reads it. References only — the name and icon come
    from the subscriptions catalog the client already has."""

    id: str
    subscription_id: str
    due_on: str
    amount: int
    currency: str
    status: str
    movement_id: str | None

    @classmethod
    def from_domain(cls, charge: SubscriptionCharge) -> "ChargeDTO":
        return cls(
            id=charge.id,
            subscription_id=charge.subscription_id,
            due_on=charge.due_on,
            amount=charge.amount,
            currency=charge.currency,
            status=charge.status,
            movement_id=charge.movement_id,
        )


class ChargesListDTO(BaseModel):
    charges: list[ChargeDTO]


class ListChargesInputDTO(BaseModel):
    user_id: UUID
    status: str | None = None


class SettleChargeInputDTO(BaseModel):
    user_id: UUID
    charge_id: str
    amount: int | None = None
    """What was really charged, when the price differs from the subscription's."""
