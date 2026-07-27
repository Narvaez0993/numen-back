from uuid import UUID

from pydantic import BaseModel


class UpdatePreferencesInputDTO(BaseModel):
    """Partial update: `None` means "leave this preference untouched"."""

    user_id: UUID
    language: str | None = None
    currency: str | None = None
    theme: str | None = None
    objective: str | None = None
    """What the user is here for: `gastos` | `ahorrar` | `deudas`. Decides which
    figure Home leads with."""
