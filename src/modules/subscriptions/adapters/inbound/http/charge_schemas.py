from pydantic import BaseModel, Field


class ConfirmChargeRequest(BaseModel):
    amount: int | None = Field(default=None, gt=0)
    """What was really charged, when it differs from the subscription's amount."""


class ChargeResponse(BaseModel):
    id: str
    subscription_id: str
    """The client resolves the name and icon from the subscriptions catalog it
    already caches — the charge carries references only."""
    due_on: str
    amount: int
    currency: str
    status: str
    """`pending` | `confirmed` | `auto` | `skipped`. `auto` means the confirmation
    window closed without an answer, so it was registered."""
    movement_id: str | None


class ChargesListResponse(BaseModel):
    charges: list[ChargeResponse]
