from dataclasses import dataclass

from src.modules.subscriptions.application.dto.subscription import SubscriptionDTO
from src.modules.subscriptions.application.dto.subscription_commands import (
    CreateSubscriptionInputDTO,
)
from src.modules.subscriptions.application.ports.subscription_repository import (
    SubscriptionRepository,
)
from src.modules.subscriptions.application.services.subscription_references import (
    SubscriptionReferences,
)
from src.modules.subscriptions.domain.entities.subscription import Subscription
from src.modules.subscriptions.domain.validation import (
    build_source_ref,
    clean_name,
    ensure_amount,
    ensure_charge_date,
    ensure_color,
    ensure_frequency,
    ensure_icon,
)
from src.shared.application.ports.clock import Clock


@dataclass
class CreateSubscriptionUseCase:
    """Registers a recurring charge. No transaction: one document, no money moved."""

    subscription_repository: SubscriptionRepository
    references: SubscriptionReferences
    clock: Clock

    async def execute(self, input_dto: CreateSubscriptionInputDTO) -> SubscriptionDTO:
        source = build_source_ref(input_dto.source_type, input_dto.source_id)
        await self.references.ensure_source(input_dto.user_id, input_dto.currency, source)
        await self.references.ensure_category(input_dto.user_id, input_dto.category_id)

        subscription = Subscription.create(
            user_id=input_dto.user_id,
            name=clean_name(input_dto.name),
            amount=ensure_amount(input_dto.amount),
            currency=input_dto.currency,
            frequency=ensure_frequency(input_dto.frequency),
            first_charge_on=ensure_charge_date(input_dto.first_charge_on),
            source=source,
            category_id=input_dto.category_id,
            icon=ensure_icon(input_dto.icon),
            color=ensure_color(input_dto.color),
            created_at=self.clock.now(),
        )
        await self.subscription_repository.save(subscription)
        return SubscriptionDTO.from_domain(subscription, input_dto.today)
