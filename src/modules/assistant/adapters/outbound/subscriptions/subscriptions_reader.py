from dataclasses import dataclass
from uuid import UUID

from src.modules.assistant.application.ports.subscriptions_reader import (
    SubscriptionsView,
    SubscriptionView,
    UpcomingChargeView,
)
from src.modules.subscriptions.application.dto.subscription_commands import (
    ListSubscriptionsInputDTO,
)
from src.modules.subscriptions.application.use_cases.list_subscriptions import (
    ListSubscriptionsUseCase,
)
from src.modules.subscriptions.application.use_cases.list_upcoming_charges import (
    ListUpcomingChargesInputDTO,
    ListUpcomingChargesUseCase,
)


@dataclass
class SubscriptionsSubscriptionsReader:
    """`SubscriptionsReader` backed by subscriptions. Upcoming charges travel
    with references only, so this adapter joins the names the model talks in."""

    list_subscriptions: ListSubscriptionsUseCase
    list_upcoming_charges: ListUpcomingChargesUseCase

    async def subscriptions(self, user_id: UUID, currency: str, today: str) -> SubscriptionsView:
        output = await self.list_subscriptions.execute(
            ListSubscriptionsInputDTO(user_id=user_id, currency=currency, today=today)
        )
        return SubscriptionsView(
            monthly_total=output.monthly,
            yearly_total=output.yearly,
            subscriptions=tuple(
                SubscriptionView(
                    id=s.id,
                    name=s.name,
                    amount=s.amount,
                    frequency=s.frequency,
                    next_charge_on=s.next_charge_on,
                )
                for s in output.subscriptions
            ),
        )

    async def upcoming_charges(
        self, user_id: UUID, currency: str, date_from: str, date_to: str, limit: int = 10
    ) -> tuple[UpcomingChargeView, ...]:
        subscriptions = await self.list_subscriptions.execute(
            ListSubscriptionsInputDTO(user_id=user_id, currency=currency, today=date_from)
        )
        names = {s.id: s.name for s in subscriptions.subscriptions}
        output = await self.list_upcoming_charges.execute(
            ListUpcomingChargesInputDTO(
                user_id=user_id, date_from=date_from, date_to=date_to, limit=limit
            )
        )
        return tuple(
            UpcomingChargeView(
                subscription_id=c.subscription_id,
                subscription_name=names.get(c.subscription_id, "?"),
                amount=c.amount,
                due_on=c.charge_on,
                status=c.status,
                charge_id=c.charge_id,
            )
            for c in output.charges
        )
