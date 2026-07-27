from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

Frequency = Literal["weekly", "monthly", "yearly"]
SourceType = Literal["account", "credit_card"]

ALLOWED_FREQUENCIES: frozenset[str] = frozenset({"weekly", "monthly", "yearly"})
ALLOWED_SOURCE_TYPES: frozenset[str] = frozenset({"account", "credit_card"})
MAX_NAME_LENGTH = 40
# Sanity bound for money in minor units, same as accounts and movements.
MAX_AMOUNT = 10**15


@dataclass(frozen=True)
class SourceRef:
    """Where the charge is taken from: an account or a credit card.

    Declared here instead of imported from `movements`: this module states what it
    needs and its adapters translate (see `SourceReader`). Most subscriptions are
    charged to a card, so both kinds have to be expressible.
    """

    type: SourceType
    id: str


@dataclass(frozen=True)
class Subscription:
    """A recurring charge the user expects — a **commitment**, not a fact.

    It never moves money on its own. What moves money is the `SubscriptionCharge`
    that opens on the due date and becomes a movement once confirmed (or after the
    confirmation window closes).

    The cadence is `frequency` + `first_charge_on` (an anchor date) rather than a
    number of days: "every 30 days" drifts about five days a year for a monthly
    charge, so the day of the month would slowly stop matching the real one. Every
    charge date is derived from the anchor — see `schedule.py`.

    `amount` is positive, in the minor unit of `currency`. `active=False` is the
    pause: it stops opening charges without losing the subscription's history.
    """

    id: str
    user_id: UUID
    name: str
    amount: int
    currency: str
    frequency: Frequency
    first_charge_on: str
    source: SourceRef
    category_id: str | None
    icon: str
    color: str
    active: bool
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        name: str,
        amount: int,
        currency: str,
        frequency: Frequency,
        first_charge_on: str,
        source: SourceRef,
        category_id: str | None,
        icon: str,
        color: str,
        created_at: datetime,
    ) -> "Subscription":
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            amount=amount,
            currency=currency,
            frequency=frequency,
            first_charge_on=first_charge_on,
            source=source,
            category_id=category_id,
            icon=icon,
            color=color,
            active=True,
            created_at=created_at,
        )

    def with_changes(self, **changes: object) -> "Subscription":
        """A patched copy. Frozen on purpose: an edit produces a new value."""
        return replace(self, **changes)  # type: ignore[arg-type]
