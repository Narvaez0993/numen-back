"""Field and coherence rules for a movement, shared by create and update.

The coherence table is the interesting part — each type demands a different shape:

| type       | source            | destination      | category    |
|------------|-------------------|------------------|-------------|
| type       | source              | destination      | category    |
|------------|---------------------|------------------|-------------|
| `expense`  | required, held-aside forbidden | forbidden | optional |
| `income`   | required, account   | forbidden        | optional    |
| `transfer` | required            | required, differs| forbidden   |

`income` is restricted to accounts in v1: money arriving on a card is a refund, a
niche case that already has an exit (adjusting the debt by hand in Accounts moves
the anchor correctly).

A `goal` (a pocket you promised yourself) and a `debt` (a claim on someone else) both
hold money **aside** rather than hold it, so each can only be a **transfer endpoint**
(money in, money out) and never both ends at once: you cannot spend from a pocket or
lend straight out of an IOU — passing through a real account first is the honest path.

That is what makes lending truthful. Handing a friend money is not spending it: cash
becomes a claim and you are no poorer, so it travels as a transfer and the month's
expenses do not move. The expense appears only if the debt is written off — the moment
the loss actually happens.

Which is the one exception below: an `expense` **out of a debt** is that write-off, and
the only way the loss can be booked without touching an account that was already
debited when the money was lent. A goal has no such moment — you cannot lose a pocket
of your own money — so it stays a transfer endpoint and nothing else. No HTTP request
can reach this shape either: `REQUEST_SOURCE_TYPES` excludes `debt`, so only the debts
module can mint it, through its port.
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

#: Sources that hold money aside instead of holding it: a pocket you promised
#: yourself, and a claim on someone else. Neither is a place you spend from or
#: earn into — money only ever *passes* between them and a real account.
_HELD_ASIDE: frozenset[str] = frozenset({"goal", "debt"})


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
        # Both ends held aside is not a move of the user's cash, it is bookkeeping
        # between two ledgers — and there is no honest balance to debit.
        if source.type in _HELD_ASIDE and destination.type in _HELD_ASIDE:
            raise InvalidMovementError(
                "A transfer needs a real account or card on at least one end"
            )
        return

    if destination is not None:
        raise InvalidMovementError(f"A {movement_type} does not take a destination")
    # The write-off: giving up on a claim IS the expense, and it comes out of the
    # claim, not out of an account the money already left.
    if source.type == "debt" and movement_type == "expense":
        return
    if source.type in _HELD_ASIDE:
        raise InvalidMovementError(f"A {source.type} can only be a transfer endpoint")
    if movement_type == "income" and source.type != "account":
        raise InvalidMovementError("Income can only arrive on an account")
