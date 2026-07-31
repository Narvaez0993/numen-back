"""Dismiss hides an output from the feed — never from the shelf."""

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel

from src.modules.assistant.application.dto.outputs import AgentOutputDTO
from src.modules.assistant.application.ports.agent_output_repository import (
    AgentOutputRepository,
)
from src.modules.assistant.domain.errors import AgentOutputNotFoundError
from src.shared.application.ports.clock import Clock


class DismissOutputInputDTO(BaseModel):
    user_id: UUID
    output_id: str


@dataclass
class DismissOutputUseCase:
    outputs: AgentOutputRepository
    clock: Clock

    async def execute(self, input_dto: DismissOutputInputDTO) -> AgentOutputDTO:
        output = await self.outputs.dismiss(
            input_dto.user_id, input_dto.output_id, self.clock.now()
        )
        if output is None:
            raise AgentOutputNotFoundError()
        return AgentOutputDTO.from_domain(output)
