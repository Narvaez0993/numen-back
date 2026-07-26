from dataclasses import dataclass

from src.modules.subscriptions.application.dto.subscription import SubscriptionDTO
from src.modules.subscriptions.application.dto.subscription_commands import (
    UpdateSubscriptionInputDTO,
)
from src.modules.subscriptions.application.ports.subscription_repository import (
    SubscriptionRepository,
)
from src.modules.subscriptions.application.services.subscription_references import (
    SubscriptionReferences,
)
from src.modules.subscriptions.domain.entities.subscription import Subscription
from src.modules.subscriptions.domain.errors import SubscriptionNotFoundError
from src.modules.subscriptions.domain.validation import (
    build_source_ref,
    clean_name,
    ensure_amount,
    ensure_charge_date,
    ensure_color,
    ensure_frequency,
    ensure_icon,
)


@dataclass
class UpdateSubscriptionUseCase:
    """Patches a subscription. Absent fields keep their stored value.

    Editing the amount only affects **future** charges: a charge that already
    opened froze its amount, so a price change never rewrites what was owed
    yesterday.
    """

    subscription_repository: SubscriptionRepository
    references: SubscriptionReferences

    async def execute(self, input_dto: UpdateSubscriptionInputDTO) -> SubscriptionDTO:
        current = await self.subscription_repository.find(
            input_dto.user_id, input_dto.subscription_id
        )
        if current is None:
            raise SubscriptionNotFoundError()

        updated = self._patch(current, input_dto)

        if updated.source != current.source:
            await self.references.ensure_source(
                input_dto.user_id, input_dto.currency, updated.source
            )
        if updated.category_id != current.category_id:
            await self.references.ensure_category(input_dto.user_id, updated.category_id)

        await self.subscription_repository.save(updated)
        return SubscriptionDTO.from_domain(updated, input_dto.today)

    @staticmethod
    def _patch(current: Subscription, input_dto: UpdateSubscriptionInputDTO) -> Subscription:
        source = current.source
        if input_dto.source_type is not None or input_dto.source_id is not None:
            source = build_source_ref(
                input_dto.source_type or current.source.type,
                input_dto.source_id or current.source.id,
            )

        return current.with_changes(
            name=current.name if input_dto.name is None else clean_name(input_dto.name),
            amount=(
                current.amount if input_dto.amount is None else ensure_amount(input_dto.amount)
            ),
            frequency=(
                current.frequency
                if input_dto.frequency is None
                else ensure_frequency(input_dto.frequency)
            ),
            first_charge_on=(
                current.first_charge_on
                if input_dto.first_charge_on is None
                else ensure_charge_date(input_dto.first_charge_on)
            ),
            source=source,
            category_id=(
                current.category_id if input_dto.category_id is None else input_dto.category_id
            ),
            icon=current.icon if input_dto.icon is None else ensure_icon(input_dto.icon),
            color=current.color if input_dto.color is None else ensure_color(input_dto.color),
            active=current.active if input_dto.active is None else input_dto.active,
        )
