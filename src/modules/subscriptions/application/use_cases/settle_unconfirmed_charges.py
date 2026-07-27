import logging
from dataclasses import dataclass
from datetime import timedelta

from src.modules.subscriptions.application.ports.charge_repository import ChargeRepository
from src.modules.subscriptions.application.services.charge_settlement import ChargeSettlement
from src.modules.subscriptions.domain.errors import SubscriptionNotFoundError
from src.modules.subscriptions.domain.schedule import CONFIRMATION_WINDOW_HOURS
from src.shared.application.ports.clock import Clock

logger = logging.getLogger(__name__)


@dataclass
class SettleUnconfirmedChargesUseCase:
    """Registers the charges nobody answered within the confirmation window.

    The user's decision: ask first, and if there is no answer in
    `CONFIRMATION_WINDOW_HOURS`, register it anyway — a charge that really happened
    should not be missing from the ledger because the phone was in a pocket.

    Every settled charge is reversible: it produced a normal movement, so deleting it
    reverts the balances exactly like any other (see the delete use case in
    `movements`). That is what makes this safe enough to be automatic.

    One failure never stops the batch: another user's subscription being deleted
    mid-window must not leave everyone else's charges pending forever.
    """

    charge_repository: ChargeRepository
    settlement: ChargeSettlement
    clock: Clock

    async def execute(self) -> int:
        """Returns how many charges were registered, for the job log."""
        deadline = self.clock.now() - timedelta(hours=CONFIRMATION_WINDOW_HOURS)
        settled = 0
        for charge in await self.charge_repository.list_pending_before(deadline):
            try:
                await self.settlement.settle(charge, status="auto")
                settled += 1
            except SubscriptionNotFoundError:
                logger.info(
                    "subscription_charge_orphaned",
                    extra={"charge_id": charge.id, "subscription_id": charge.subscription_id},
                )
            except Exception:
                logger.exception(
                    "subscription_charge_settle_failed", extra={"charge_id": charge.id}
                )
        return settled
