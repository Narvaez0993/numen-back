from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

MovementType = Literal["expense", "income", "transfer"]
SourceType = Literal["account", "credit_card"]
CapturedVia = Literal["manual", "voice", "photo", "text"]

ALLOWED_TYPES: frozenset[str] = frozenset({"expense", "income", "transfer"})
ALLOWED_SOURCE_TYPES: frozenset[str] = frozenset({"account", "credit_card"})
ALLOWED_CAPTURED_VIA: frozenset[str] = frozenset({"manual", "voice", "photo", "text"})
MAX_DESCRIPTION_LENGTH = 80
# Sanity bound for money in minor units, same as accounts.
MAX_AMOUNT = 10**15


@dataclass(frozen=True)
class SourceRef:
    """Where the money sits: an account or a credit card.

    Two collections hold sources, so a reference needs both parts. Movements only
    ever carry the reference — resolving it is the ledger's job.
    """

    type: SourceType
    id: str


@dataclass(frozen=True)
class Movement:
    """A registered movement of money: expense, income or transfer.

    `amount` is always **positive** in the minor unit of `currency`; the sign is a
    consequence of `type`, never stored (a negative amount on an `expense` would
    be an impossible state we would have to validate anyway).

    `occurred_on` is a date without time (`YYYY-MM-DD`) — the day the user says it
    happened, immune to timezones. `created_at` is the instant we recorded it and
    breaks ties in the listing order.
    """

    id: str
    user_id: UUID
    type: MovementType
    description: str
    amount: int
    currency: str
    source: SourceRef
    destination: SourceRef | None
    category_id: str | None
    occurred_on: str
    captured_via: CapturedVia
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        type: MovementType,
        description: str,
        amount: int,
        currency: str,
        source: SourceRef,
        destination: SourceRef | None,
        category_id: str | None,
        occurred_on: str,
        captured_via: CapturedVia,
        created_at: datetime,
    ) -> "Movement":
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            type=type,
            description=description,
            amount=amount,
            currency=currency,
            source=source,
            destination=destination,
            category_id=category_id,
            occurred_on=occurred_on,
            captured_via=captured_via,
            created_at=created_at,
        )

    def deltas(self) -> tuple[tuple[SourceRef, int], ...]:
        """The money effect of this movement, as a change in position per source.

        This is the **whole cash-basis rule**, in one place:

        | type       | effect                                          |
        |------------|-------------------------------------------------|
        | `expense`  | source -amount                                  |
        | `income`   | source +amount                                  |
        | `transfer` | source -amount, destination +amount             |

        Whoever applies a delta translates it per source kind: an account moves
        its `balance` by the delta, a credit card moves its `debt` by the
        *opposite* (a positive delta always improves your position). Every
        cash-basis case falls out of that: a card charge raises debt, a card
        payment lowers debt and balance, a cash advance does the reverse, and a
        transfer between accounts leaves the net balance untouched.
        """
        if self.type == "expense":
            return ((self.source, -self.amount),)
        if self.type == "income":
            return ((self.source, self.amount),)
        # A transfer always has a destination (guaranteed by validation).
        assert self.destination is not None
        return ((self.source, -self.amount), (self.destination, self.amount))

    def reverted_deltas(self) -> tuple[tuple[SourceRef, int], ...]:
        """The deltas that undo this movement — used to edit or delete it."""
        return tuple((ref, -delta) for ref, delta in self.deltas())

    def with_updates(
        self,
        *,
        description: str | None = None,
        amount: int | None = None,
        source: SourceRef | None = None,
        destination: SourceRef | None = None,
        category_id: str | None = None,
        occurred_on: str | None = None,
    ) -> "Movement":
        """A new version of this movement. `type` never changes: switching an
        expense into a transfer is a different movement, not an edit."""
        return replace(
            self,
            description=self.description if description is None else description,
            amount=self.amount if amount is None else amount,
            source=self.source if source is None else source,
            destination=self.destination if destination is None else destination,
            category_id=self.category_id if category_id is None else category_id,
            occurred_on=self.occurred_on if occurred_on is None else occurred_on,
        )
