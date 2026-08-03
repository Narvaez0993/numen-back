from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel

from src.modules.assistant.application.dto.outputs import AgentOutputDTO
from src.modules.assistant.application.ports.agent_output_repository import (
    AgentOutputRepository,
)
from src.modules.assistant.domain.errors import AgentOutputNotFoundError


class GetOutputInputDTO(BaseModel):
    user_id: UUID
    output_id: str


@dataclass
class GetOutputUseCase:
    outputs: AgentOutputRepository

    async def execute(self, input_dto: GetOutputInputDTO) -> AgentOutputDTO:
        output = await self.outputs.find(input_dto.user_id, input_dto.output_id)
        if output is None:
            raise AgentOutputNotFoundError()
        return AgentOutputDTO.from_domain(output)
