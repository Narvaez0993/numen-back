"""Field rules for a subscription, shared by create and update.

There is no "not in the future" rule here — unlike a movement, a subscription is
allowed to be scheduled ahead (that is the whole point), and it is also allowed to
start in the past (a charge you have had for a year). What protects the user from a
past anchor is the opener, which never charges a date before the subscription
existed (see `use_cases/open_due_charges.py`).
"""

from datetime import date
from typing import cast

from src.modules.subscriptions.domain.entities.subscription import (
    ALLOWED_FREQUENCIES,
    ALLOWED_SOURCE_TYPES,
    MAX_AMOUNT,
    MAX_NAME_LENGTH,
    Frequency,
    SourceRef,
    SourceType,
)
from src.modules.subscriptions.domain.errors import InvalidSubscriptionError

ALLOWED_COLORS: frozenset[str] = frozenset({"mint", "coral", "purple", "amber", "pink", "neutral"})
DEFAULT_ICON = "refresh"
DEFAULT_COLOR = "amber"


def clean_name(raw: str) -> str:
    name = raw.strip()
    if not name or len(name) > MAX_NAME_LENGTH:
        raise InvalidSubscriptionError(f"Name must be 1-{MAX_NAME_LENGTH} characters")
    return name


def ensure_amount(value: int) -> int:
    if value <= 0:
        raise InvalidSubscriptionError("Amount must be greater than zero")
    if value > MAX_AMOUNT:
        raise InvalidSubscriptionError("Amount is out of range")
    return value


def ensure_frequency(raw: str) -> Frequency:
    if raw not in ALLOWED_FREQUENCIES:
        raise InvalidSubscriptionError(f"Invalid frequency: {raw}")
    return cast(Frequency, raw)


def ensure_charge_date(raw: str) -> str:
    """The anchor date in `YYYY-MM-DD` — a day, never a display string."""
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise InvalidSubscriptionError(f"Invalid date: {raw} (expected YYYY-MM-DD)") from exc
    return parsed.isoformat()


def build_source_ref(source_type: str, source_id: str) -> SourceRef:
    if source_type not in ALLOWED_SOURCE_TYPES:
        raise InvalidSubscriptionError(f"Invalid source type: {source_type}")
    if not source_id.strip():
        raise InvalidSubscriptionError("Source id is required")
    return SourceRef(type=cast(SourceType, source_type), id=source_id)


def ensure_color(raw: str | None) -> str:
    if raw is None:
        return DEFAULT_COLOR
    if raw not in ALLOWED_COLORS:
        raise InvalidSubscriptionError(f"Invalid color: {raw}")
    return raw


def ensure_icon(raw: str | None) -> str:
    if raw is None:
        return DEFAULT_ICON
    icon = raw.strip()
    if not icon:
        raise InvalidSubscriptionError("Icon cannot be empty")
    return icon
