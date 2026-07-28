from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel

from src.modules.assistant.application.dto.chat import (
    CounterDTO,
    MessagesCounterDTO,
    UsageOutputDTO,
)
from src.modules.assistant.application.ports.usage_counters import UsageCounters
from src.modules.assistant.application.pricing import PlanLimits


class UsageInputDTO(BaseModel):
    user_id: UUID
    tier: str
    today: str


@dataclass
class GetUsageUseCase:
    """The two meters, always answerable — a month with no row is simply zeros."""

    usage_counters: UsageCounters
    plan_limits: PlanLimits

    async def execute(self, input_dto: UsageInputDTO) -> UsageOutputDTO:
        usage = await self.usage_counters.month_usage(input_dto.user_id, input_dto.today[:7])
        return UsageOutputDTO(
            registrations=CounterDTO(
                used=usage.registrations_used,
                limit=self.plan_limits.registrations_for(input_dto.tier),
            ),
            messages=MessagesCounterDTO(
                used=usage.messages_used,
                limit=self.plan_limits.messages_for(input_dto.tier),
                grace=self.plan_limits.message_grace,
            ),
        )
