"""«Tus Cortes» — the shelf. Dismissed outputs still show here: dismissing
hides a card from the feed, it never rewrites history."""

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.assistant.application.dto.outputs import AgentOutputDTO
from src.modules.assistant.application.ports.agent_output_repository import (
    AgentOutputRepository,
)
from src.modules.assistant.domain.entities.agent_output import MONTHLY_SUMMARY


class ListOutputsInputDTO(BaseModel):
    user_id: UUID
    kind: str = MONTHLY_SUMMARY
    limit: int = Field(default=24, ge=1, le=48)


class ListOutputsOutputDTO(BaseModel):
    outputs: list[AgentOutputDTO]


@dataclass
class ListOutputsUseCase:
    outputs: AgentOutputRepository

    async def execute(self, input_dto: ListOutputsInputDTO) -> ListOutputsOutputDTO:
        found = await self.outputs.latest(input_dto.user_id, input_dto.kind, input_dto.limit)
        return ListOutputsOutputDTO(outputs=[AgentOutputDTO.from_domain(o) for o in found])
