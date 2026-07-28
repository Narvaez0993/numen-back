"""Field and coherence rules for a movement, shared by create and update.

The coherence table is the interesting part — each type demands a different shape:

| type       | source            | destination      | category    |
|------------|-------------------|------------------|-------------|
| `expense`  | required, no goal | forbidden        | optional    |
| `income`   | required, account | forbidden        | optional    |
| `transfer` | required          | required, differs| forbidden   |

`income` is restricted to accounts in v1: money arriving on a card is a refund, a
niche case that already has an exit (adjusting the debt by hand in Accounts moves
the anchor correctly).

A `goal` is a pocket of set-aside money, so it can only be a **transfer endpoint**
(money in, money out) and never both ends at once: you cannot spend from a pocket
or move between pockets — withdrawing to an account first is the honest path.
"""

from datetime import date, timedelta
from typing import cast

from src.modules.movements.domain.entities.movement import (
    ALLOWED_CAPTURED_VIA,
    ALLOWED_SOURCE_TYPES,
    ALLOWED_TYPES,
    MAX_AMOUNT,
    MAX_DESCRIPTION_LENGTH,
    CapturedVia,
    MovementType,
    SourceRef,
    SourceType,
)
from src.modules.movements.domain.errors import InvalidMovementError


def ensure_type(raw: str) -> MovementType:
    if raw not in ALLOWED_TYPES:
        raise InvalidMovementError(f"Invalid movement type: {raw}")
    return cast(MovementType, raw)


def ensure_captured_via(raw: str) -> CapturedVia:
    if raw not in ALLOWED_CAPTURED_VIA:
        raise InvalidMovementError(f"Invalid capture method: {raw}")
    return cast(CapturedVia, raw)


def clean_description(raw: str) -> str:
    description = raw.strip()
    if not description or len(description) > MAX_DESCRIPTION_LENGTH:
        raise InvalidMovementError(f"Description must be 1-{MAX_DESCRIPTION_LENGTH} characters")
    return description


def ensure_amount(value: int) -> int:
    """Amounts are positive: the sign belongs to the type, not to the number."""
    if value <= 0:
        raise InvalidMovementError("Amount must be greater than zero")
    if value > MAX_AMOUNT:
        raise InvalidMovementError("Amount is out of range")
    return value


def ensure_occurred_on(raw: str) -> str:
    """A real calendar date in `YYYY-MM-DD`, never a display string."""
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise InvalidMovementError(f"Invalid date: {raw} (expected YYYY-MM-DD)") from exc
    return parsed.isoformat()


def ensure_not_future(occurred_on: str, today: date) -> str:
    """You register what already happened — a scheduled charge is a subscription.

    One day of grace on purpose: `today` is the server's date in UTC and a client
    in UTC+13 can legitimately be a day ahead, so a strict comparison would reject
    their real "today". Still catches the mistyped year.
    """
    if date.fromisoformat(occurred_on) > today + timedelta(days=1):
        raise InvalidMovementError(f"Date {occurred_on} is in the future")
    return occurred_on


def build_source_ref(source_type: str, source_id: str) -> SourceRef:
    if source_type not in ALLOWED_SOURCE_TYPES:
        raise InvalidMovementError(f"Invalid source type: {source_type}")
    if not source_id.strip():
        raise InvalidMovementError("Source id is required")
    return SourceRef(type=cast(SourceType, source_type), id=source_id)


def ensure_shape(
    movement_type: MovementType,
    source: SourceRef,
    destination: SourceRef | None,
    category_id: str | None,
) -> None:
    """Enforce the coherence table above."""
    if movement_type == "transfer":
        if destination is None:
            raise InvalidMovementError("A transfer needs a destination")
        if destination == source:
            raise InvalidMovementError("A transfer needs two different sources")
        if category_id is not None:
            raise InvalidMovementError("A transfer does not take a category")
        if source.type == "goal" and destination.type == "goal":
            raise InvalidMovementError("A transfer cannot run between two goals")
        return

    if destination is not None:
        raise InvalidMovementError(f"A {movement_type} does not take a destination")
    if source.type == "goal":
        raise InvalidMovementError("A goal can only be a transfer endpoint")
    if movement_type == "income" and source.type != "account":
        raise InvalidMovementError("Income can only arrive on an account")
