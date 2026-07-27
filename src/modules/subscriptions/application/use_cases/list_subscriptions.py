from dataclasses import dataclass

from src.modules.subscriptions.application.dto.subscription import SubscriptionsOverviewDTO
from src.modules.subscriptions.application.dto.subscription_commands import (
    ListSubscriptionsInputDTO,
)
from src.modules.subscriptions.application.ports.subscription_repository import (
    SubscriptionRepository,
)


@dataclass
class ListSubscriptionsUseCase:
    subscription_repository: SubscriptionRepository

    async def execute(self, input_dto: ListSubscriptionsInputDTO) -> SubscriptionsOverviewDTO:
        subscriptions = await self.subscription_repository.list_by_user(input_dto.user_id)
        # Soonest first: the list answers "what is about to be charged".
        subscriptions.sort(key=lambda s: (not s.active, s.first_charge_on))
        return SubscriptionsOverviewDTO.build(
            subscriptions, currency=input_dto.currency, today=input_dto.today
        )
