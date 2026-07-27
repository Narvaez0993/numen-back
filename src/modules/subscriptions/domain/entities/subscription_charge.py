from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from src.modules.subscriptions.domain.schedule import CONFIRMATION_WINDOW_HOURS

ChargeStatus = Literal["pending", "confirmed", "auto", "skipped"]

SETTLED_STATUSES: frozenset[str] = frozenset({"confirmed", "auto", "skipped"})


@dataclass(frozen=True)
class SubscriptionCharge:
    """One occurrence of a subscription, on the day it is due.

    The lifecycle is the whole feature:

    | status      | meaning                                                      |
    |-------------|--------------------------------------------------------------|
    | `pending`   | due today, waiting for the user to confirm                   |
    | `confirmed` | the user confirmed it; a movement exists                     |
    | `auto`      | the window closed without an answer, so it was registered    |
    | `skipped`   | the user said it did not happen; no movement                 |
    |             |                                                              |

    `amount` is **frozen when the charge opens**. Raising the subscription's price
    tomorrow must not rewrite what was owed today, and the user may confirm a
    different amount (the price went up) without the record contradicting itself.

    The charge is also the idempotency guard: one per `(user, subscription, due_on)`,
    enforced by a unique index, so no run of the job can charge the same day twice.
    """

    id: str
    user_id: UUID
    subscription_id: str
    due_on: str
    amount: int
    currency: str
    status: ChargeStatus
    opened_at: datetime
    settled_at: datetime | None
    movement_id: str | None

    @classmethod
    def open(
        cls,
        *,
        user_id: UUID,
        subscription_id: str,
        due_on: str,
        amount: int,
        currency: str,
        opened_at: datetime,
    ) -> "SubscriptionCharge":
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            subscription_id=subscription_id,
            due_on=due_on,
            amount=amount,
            currency=currency,
            status="pending",
            opened_at=opened_at,
            settled_at=None,
            movement_id=None,
        )

    @property
    def is_settled(self) -> bool:
        return self.status in SETTLED_STATUSES

    def window_closed_at(self) -> datetime:
        return self.opened_at + timedelta(hours=CONFIRMATION_WINDOW_HOURS)

    def is_confirmable_at(self, now: datetime) -> bool:
        """Has the confirmation window closed? Then it is the engine's turn."""
        return now < self.window_closed_at()

    def settled(
        self,
        *,
        status: ChargeStatus,
        movement_id: str | None,
        settled_at: datetime,
        amount: int | None = None,
    ) -> "SubscriptionCharge":
        """`amount` records what was **really** charged when it differs."""
        return replace(
            self,
            status=status,
            movement_id=movement_id,
            settled_at=settled_at,
            amount=self.amount if amount is None else amount,
        )
