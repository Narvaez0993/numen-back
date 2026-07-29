from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4
from zlib import crc32

MAX_NAME_LENGTH = 40

# The accent palette a person can wear. `neutral` is excluded on purpose: avatars need
# a colour, and grey reads as "disabled".
COLOR_PALETTE: tuple[str, ...] = ("mint", "purple", "amber", "coral", "pink")


def name_key(name: str) -> str:
    """How two spellings become one person: trimmed, single-spaced, case-folded.

    "Juan Felipe", " juan  felipe " and "JUAN FELIPE" are the same counterparty. The
    unique index stores this key, so the rule lives in the store and not only here.
    """
    return " ".join(name.split()).casefold()


def color_for(name: str) -> str:
    """A stable colour derived from the name — deterministic, so retrying a creation
    cannot produce a different-looking person. CRC32, not `hash()`: Python salts the
    latter per process."""
    return COLOR_PALETTE[crc32(name_key(name).encode()) % len(COLOR_PALETTE)]


@dataclass(frozen=True)
class Counterparty:
    """Someone the user owes or who owes them. Not an app user: just a name.

    Created inline the first time a debt names them — there is no "manage people"
    screen to fill in first, because the person only matters while money is between
    you. The prototype also stored an `initial`; it is derived from the name, so it
    never made it here.
    """

    id: str
    user_id: UUID
    name: str
    color: str
    created_at: datetime

    @classmethod
    def create(cls, *, user_id: UUID, name: str, created_at: datetime) -> "Counterparty":
        clean = " ".join(name.split())
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            name=clean,
            color=color_for(clean),
            created_at=created_at,
        )
