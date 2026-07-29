from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID, uuid4

from src.modules.assistant.domain.errors import DraftNotPendingError

PENDING = "pending"
CONFIRMED = "confirmed"
DISCARDED = "discarded"

# What the user may change before confirming. Identity fields (id, user, currency)
# and lifecycle fields are not overridable — a draft edited into a different user's
# pocket is not an edit.
OVERRIDABLE_FIELDS: frozenset[str] = frozenset(
    {
        "type",
        "description",
        "amount",
        "source_type",
        "source_id",
        "destination_type",
        "destination_id",
        "category_id",
        "occurred_on",
    }
)


@dataclass(frozen=True)
class MovementDraft:
    """A movement the agent understood but the user has not confirmed.

    The language model never writes to the ledger: it stages one of these, the
    user confirms (possibly after editing), and only then does the movement exist
    — recorded through the same use case the manual form uses. The draft keeps
    its `status` forever so the chat history always shows what became of it.
    """

    id: str
    user_id: UUID
    currency: str
    type: str
    """`expense` | `income` | `transfer` — movements re-validates on confirm."""
    description: str
    amount: int
    """Positive, in the minor unit of `currency`."""
    source_type: str
    source_id: str
    destination_type: str | None
    destination_id: str | None
    category_id: str | None
    occurred_on: str
    status: str
    movement_id: str | None
    created_at: datetime
    captured_via: str = "text"
    """How the words reached us (`text` | `voice`) — provenance is a fact of the
    capture context, never something the model (or an edit) gets to claim."""

    @property
    def pending(self) -> bool:
        return self.status == PENDING

    @classmethod
    def stage(
        cls,
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
        created_at: datetime,
        captured_via: str = "text",
    ) -> "MovementDraft":
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            currency=currency,
            type=type,
            description=" ".join(description.split()),
            amount=amount,
            source_type=source_type,
            source_id=source_id,
            destination_type=destination_type,
            destination_id=destination_id,
            category_id=category_id,
            occurred_on=occurred_on,
            status=PENDING,
            movement_id=None,
            created_at=created_at,
            captured_via=captured_via,
        )

    def apply_overrides(self, overrides: dict[str, object]) -> "MovementDraft":
        """The user's edits from the confirm sheet, applied to a pending draft."""
        self._ensure_pending()
        unknown = set(overrides) - OVERRIDABLE_FIELDS
        if unknown:
            raise ValueError(f"Field(s) not overridable: {sorted(unknown)}")
        return replace(self, **overrides)  # type: ignore[arg-type]

    def confirm(self, movement_id: str) -> "MovementDraft":
        self._ensure_pending()
        return replace(self, status=CONFIRMED, movement_id=movement_id)

    def discard(self) -> "MovementDraft":
        self._ensure_pending()
        return replace(self, status=DISCARDED)

    def _ensure_pending(self) -> None:
        if not self.pending:
            raise DraftNotPendingError()
