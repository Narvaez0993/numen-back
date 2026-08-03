from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.assistant.application.ports.insight_dismissals import InsightDismissals


class DismissInsightInputDTO(BaseModel):
    user_id: UUID
    key: str = Field(min_length=1, max_length=120)


@dataclass
class DismissInsightUseCase:
    """Idempotent by design: dismissing twice is one dismissal."""

    dismissals: InsightDismissals

    async def execute(self, input_dto: DismissInsightInputDTO) -> None:
        await self.dismissals.dismiss(input_dto.user_id, input_dto.key, datetime.now(UTC))
