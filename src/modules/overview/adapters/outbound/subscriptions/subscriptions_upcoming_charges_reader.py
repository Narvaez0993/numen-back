from dataclasses import dataclass
from uuid import UUID

from src.modules.overview.application.ports.upcoming_charges_reader import UpcomingChargeView
from src.modules.subscriptions.application.use_cases.list_upcoming_charges import (
    ListUpcomingChargesInputDTO,
    ListUpcomingChargesUseCase,
)


@dataclass
class SubscriptionsUpcomingChargesReader:
    """`UpcomingChargesReader` backed by the subscriptions module.

    Talks to its use case, never to its collections: the cadence rule and the state of
    each charge stay owned by the module that defines them, and this is only the
    translation into what Home shows.
    """

    list_upcoming: ListUpcomingChargesUseCase

    async def upcoming(
        self, user_id: UUID, date_from: str, date_to: str, limit: int
    ) -> list[UpcomingChargeView]:
        output = await self.list_upcoming.execute(
            ListUpcomingChargesInputDTO(
                user_id=user_id, date_from=date_from, date_to=date_to, limit=limit
            )
        )
        return [
            UpcomingChargeView(
                subscription_id=charge.subscription_id,
                charge_on=charge.charge_on,
                amount=charge.amount,
                status=charge.status,
                charge_id=charge.charge_id,
            )
            for charge in output.charges
        ]
