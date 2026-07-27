from dataclasses import dataclass
from datetime import timedelta

from src.modules.subscriptions.application.ports.charge_repository import (
    ChargeAlreadyOpenError,
    ChargeRepository,
)
from src.modules.subscriptions.application.ports.subscription_repository import (
    SubscriptionRepository,
)
from src.modules.subscriptions.domain.entities.subscription import Subscription
from src.modules.subscriptions.domain.entities.subscription_charge import SubscriptionCharge
from src.modules.subscriptions.domain.schedule import CATCH_UP_DAYS, occurrences
from src.shared.application.ports.clock import Clock


@dataclass
class OpenDueChargesUseCase:
    """Opens a pending charge for everything due today, across every tenant.

    Two guards keep this from surprising anyone:

    - it looks back only `CATCH_UP_DAYS`, so a worker that was down for an hour does
      not skip a charge and a worker that was down for a month does not dump thirty
      of them on the user;
    - it never opens a charge for a date **before the subscription existed**. An
      anchor in the past is legitimate ("I have paid this since January") and must
      not turn into six months of retroactive expenses.

    Opening is idempotent by unique index: a second run for the same day is a no-op.
    """

    subscription_repository: SubscriptionRepository
    charge_repository: ChargeRepository
    clock: Clock

    async def execute(self) -> int:
        """Returns how many charges were opened, for the job log."""
        today = self.clock.now().date()
        date_from = (today - timedelta(days=CATCH_UP_DAYS)).isoformat()
        date_to = today.isoformat()

        opened = 0
        for subscription in await self.subscription_repository.list_active():
            for due_on in occurrences(subscription, date_from, date_to):
                if self._predates(subscription, due_on):
                    continue
                if await self._open(subscription, due_on):
                    opened += 1
        return opened

    @staticmethod
    def _predates(subscription: Subscription, due_on: str) -> bool:
        return due_on < subscription.created_at.date().isoformat()

    async def _open(self, subscription: Subscription, due_on: str) -> bool:
        charge = SubscriptionCharge.open(
            user_id=subscription.user_id,
            subscription_id=subscription.id,
            due_on=due_on,
            amount=subscription.amount,
            currency=subscription.currency,
            opened_at=self.clock.now(),
        )
        try:
            await self.charge_repository.open(charge)
        except ChargeAlreadyOpenError:
            # Already opened by an earlier run — the unique index is the guard.
            return False
        return True
