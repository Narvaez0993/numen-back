from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.subscriptions.domain.entities.subscription_charge import SubscriptionCharge


class ChargeAlreadyOpenError(Exception):
    """The `(user, subscription, due_on)` charge already exists.

    Raised by the store, not by a check-then-write: a unique index is what makes two
    concurrent job runs unable to charge the same day twice. Callers treat it as
    "someone else got there first", never as a failure.
    """


class ChargeRepository(Protocol):
    async def open(self, charge: SubscriptionCharge) -> None:
        """Insert a pending charge. Raises `ChargeAlreadyOpenError` if it exists."""
        ...

    async def save(self, charge: SubscriptionCharge) -> None: ...

    async def find(self, user_id: UUID, charge_id: str) -> SubscriptionCharge | None: ...

    async def list_by_status(
        self, user_id: UUID, status: str | None = None
    ) -> list[SubscriptionCharge]: ...

    async def list_pending_before(self, deadline: datetime) -> list[SubscriptionCharge]:
        """Every tenant's pending charges opened at or before `deadline`.

        The settler's query: it runs for all users at once, so it cannot be scoped.
        """
        ...
