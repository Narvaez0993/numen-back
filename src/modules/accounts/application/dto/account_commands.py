from uuid import UUID

from pydantic import BaseModel


class CreateAccountInputDTO(BaseModel):
    """`tier` gates capacity and `currency` is the user's home currency; both are
    resolved from the caller, never taken from the request body."""

    user_id: UUID
    tier: str
    currency: str
    kind: str
    name: str
    sub: str = ""
    icon: str = ""
    color: str = ""
    balance: int = 0


class UpdateAccountInputDTO(BaseModel):
    """Partial update: `None` means "leave this field untouched"."""

    user_id: UUID
    account_id: str
    name: str | None = None
    sub: str | None = None
    icon: str | None = None
    color: str | None = None
    balance: int | None = None


class DeleteAccountInputDTO(BaseModel):
    user_id: UUID
    account_id: str
