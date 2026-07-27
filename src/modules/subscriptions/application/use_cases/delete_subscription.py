from dataclasses import dataclass

from src.modules.subscriptions.application.dto.subscription_commands import (
    DeleteSubscriptionInputDTO,
)
from src.modules.subscriptions.application.ports.subscription_repository import (
    SubscriptionRepository,
)
from src.modules.subscriptions.domain.errors import SubscriptionNotFoundError


@dataclass
class DeleteSubscriptionUseCase:
    """Forgets a subscription.

    Movements it already produced are **kept**: they are real money that moved, and
    erasing them would rewrite the user's history. To stop the charges without
    losing the subscription, patch `active` to false instead.
    """

    subscription_repository: SubscriptionRepository

    async def execute(self, input_dto: DeleteSubscriptionInputDTO) -> None:
        deleted = await self.subscription_repository.delete(
            input_dto.user_id, input_dto.subscription_id
        )
        if not deleted:
            raise SubscriptionNotFoundError()
