from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID, uuid4
from zlib import crc32

MAX_NAME_LENGTH = 40
# Sanity bound for money in minor units, same as the rest of the app.
MAX_TARGET = 10**15
MIN_TARGET = 1

DEFAULT_ICON = "target"
# The accent palette a pocket can wear; `neutral` reads as disabled, so it is out.
COLOR_PALETTE: tuple[str, ...] = ("mint", "purple", "amber", "coral", "pink")


def color_for(name: str) -> str:
    """A stable colour from the name — CRC32, not `hash()`, which Python salts per
    process; a retried creation must not mint a different-looking pocket."""
    return COLOR_PALETTE[crc32(" ".join(name.split()).casefold().encode()) % len(COLOR_PALETTE)]


@dataclass(frozen=True)
class Goal:
    """A pocket: money set aside for something, like a bank's *bolsillos*.

    The pocket holds **real money**: a contribution is a genuine `transfer` movement
    out of an account, so the account balance and the net balance drop by it. What is
    deliberately NOT here is a `saved` field — the pocket's money is the sum of those
    transfers, computed by reading them, so it cannot drift from the ledger. The
    prototype persisted `saved` and a `projectionMonth` display string, and both are
    the class of field that goes stale.

    `archived_at` is the user closing the pocket while keeping its history; both
    archiving and deleting demand the pocket be **empty** first — money hidden inside
    an archived goal would be money the app stopped showing.
    """

    id: str
    user_id: UUID
    name: str
    icon: str
    color: str
    target: int
    """Positive, in the minor unit of `currency`."""
    currency: str
    target_date: str | None
    """`YYYY-MM-DD` or nothing — enables "you need $X a month to make it"."""
    archived_at: datetime | None
    created_at: datetime

    @property
    def active(self) -> bool:
        return self.archived_at is None

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        name: str,
        target: int,
        currency: str,
        target_date: str | None,
        created_at: datetime,
    ) -> "Goal":
        clean = " ".join(name.split())
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            name=clean,
            icon=DEFAULT_ICON,
            color=color_for(clean),
            target=target,
            currency=currency,
            target_date=target_date,
            archived_at=None,
            created_at=created_at,
        )

    def with_changes(self, **changes: object) -> "Goal":
        """A patched copy. Frozen on purpose: an edit produces a new value."""
        return replace(self, **changes)  # type: ignore[arg-type]
