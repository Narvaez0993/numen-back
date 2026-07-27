from dataclasses import dataclass

from src.modules.subscriptions.application.ports.charge_repository import ChargeRepository
from src.modules.subscriptions.application.ports.expense_recorder import ExpenseRecorder
from src.modules.subscriptions.application.ports.subscription_repository import (
    SubscriptionRepository,
)
from src.modules.subscriptions.domain.entities.subscription_charge import (
    ChargeStatus,
    SubscriptionCharge,
)
from src.modules.subscriptions.domain.errors import SubscriptionNotFoundError
from src.shared.application.ports.clock import Clock
from src.shared.application.ports.unit_of_work import UnitOfWork


@dataclass
class ChargeSettlement:
    """Turns a due charge into a registered expense.

    Shared by the two ways a charge is settled — the user confirming it and the
    window closing — so both produce exactly the same movement and leave the same
    trace. Only `status` differs, and that is what later tells the user "you did not
    answer, so we registered it".

    Both writes happen in one transaction: a charge marked settled without its
    movement (or the reverse) would either lose money or charge it twice on the next
    run. The movement's own atomic write joins this transaction because the unit of
    work is re-entrant.
    """

    charge_repository: ChargeRepository
    subscription_repository: SubscriptionRepository
    expense_recorder: ExpenseRecorder
    unit_of_work: UnitOfWork
    clock: Clock

    async def settle(
        self,
        charge: SubscriptionCharge,
        *,
        status: ChargeStatus,
        amount: int | None = None,
    ) -> SubscriptionCharge:
        subscription = await self.subscription_repository.find(
            charge.user_id, charge.subscription_id
        )
        if subscription is None:
            # The subscription was deleted while its charge was pending: there is
            # nothing left to charge for, so the charge dies with it.
            raise SubscriptionNotFoundError()

        # What was really charged wins over what was expected: prices go up.
        final_amount = amount if amount is not None else charge.amount
        settled_at = self.clock.now()

        async def apply() -> SubscriptionCharge:
            recorded = await self.expense_recorder.record(
                user_id=charge.user_id,
                currency=charge.currency,
                description=subscription.name,
                amount=final_amount,
                source=subscription.source,
                category_id=subscription.category_id,
                occurred_on=charge.due_on,
                subscription_id=subscription.id,
                idempotency_key=idempotency_key(charge),
            )
            settled = charge.settled(
                status=status,
                movement_id=recorded.movement_id,
                settled_at=settled_at,
                amount=final_amount,
            )
            await self.charge_repository.save(settled)
            return settled

        return await self.unit_of_work.atomic(apply)

    async def skip(self, charge: SubscriptionCharge) -> SubscriptionCharge:
        """The charge did not happen (cancelled, refunded, a card that declined)."""
        skipped = charge.settled(status="skipped", movement_id=None, settled_at=self.clock.now())
        await self.charge_repository.save(skipped)
        return skipped


def idempotency_key(charge: SubscriptionCharge) -> str:
    """One key per subscription and due date — the same key can only spend once.

    Derived, not random: if the settler retries after a partial failure it reuses the
    key and the movements module replays the original instead of charging again.
    """
    return f"sub:{charge.subscription_id}:{charge.due_on}"
