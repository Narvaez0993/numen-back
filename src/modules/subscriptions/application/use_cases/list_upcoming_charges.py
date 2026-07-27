from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel

from src.modules.subscriptions.application.ports.charge_repository import ChargeRepository
from src.modules.subscriptions.application.ports.subscription_repository import (
    SubscriptionRepository,
)
from src.modules.subscriptions.domain.schedule import occurrences


class UpcomingChargeDTO(BaseModel):
    """A charge that is coming, or one that is already waiting for an answer.

    References only: the client resolves the name and icon from the subscriptions
    catalog it already caches, so renaming a subscription updates every view.
    """

    subscription_id: str
    charge_on: str
    amount: int
    status: str
    """`pending` — due and awaiting confirmation — or `scheduled` for a future date."""
    charge_id: str | None
    """Present only when it is `pending`: it is what confirm/skip act on."""


class UpcomingChargesDTO(BaseModel):
    charges: list[UpcomingChargeDTO]


class ListUpcomingChargesInputDTO(BaseModel):
    user_id: UUID
    date_from: str
    date_to: str
    limit: int = 5


@dataclass
class ListUpcomingChargesUseCase:
    """What is about to be charged in a date range.

    Two sources, one list: the dates the schedule produces, and the charges already
    open for them. A date whose charge is **settled** is not upcoming any more — it
    either became a movement or was skipped, and repeating it would double-count what
    the user already sees in their month.
    """

    subscription_repository: SubscriptionRepository
    charge_repository: ChargeRepository

    async def execute(self, input_dto: ListUpcomingChargesInputDTO) -> UpcomingChargesDTO:
        subscriptions = await self.subscription_repository.list_by_user(
            input_dto.user_id, only_active=True
        )
        charges = await self.charge_repository.list_by_status(input_dto.user_id)
        by_date = {(c.subscription_id, c.due_on): c for c in charges}

        upcoming: list[UpcomingChargeDTO] = []
        for subscription in subscriptions:
            for charge_on in occurrences(subscription, input_dto.date_from, input_dto.date_to):
                existing = by_date.get((subscription.id, charge_on))
                if existing is not None and existing.is_settled:
                    continue
                upcoming.append(
                    UpcomingChargeDTO(
                        subscription_id=subscription.id,
                        charge_on=charge_on,
                        # A charge that is open froze its amount; the rest quote the
                        # subscription's current one.
                        amount=existing.amount if existing else subscription.amount,
                        status="pending" if existing else "scheduled",
                        charge_id=existing.id if existing else None,
                    )
                )

        # Soonest first, and the ones already waiting for an answer come first within
        # a day: they are the ones the user can act on.
        upcoming.sort(key=lambda c: (c.charge_on, c.status != "pending"))
        return UpcomingChargesDTO(charges=upcoming[: input_dto.limit])
