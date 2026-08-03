"""`read_at` is written once — the "Nuevo" pill dies the first time you look,
and replaying an old Corte never pretends it is news again."""

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel

from src.modules.assistant.application.dto.outputs import AgentOutputDTO
from src.modules.assistant.application.ports.agent_output_repository import (
    AgentOutputRepository,
)
from src.modules.assistant.domain.errors import AgentOutputNotFoundError
from src.shared.application.ports.clock import Clock


class MarkOutputReadInputDTO(BaseModel):
    user_id: UUID
    output_id: str


@dataclass
class MarkOutputReadUseCase:
    outputs: AgentOutputRepository
    clock: Clock

    async def execute(self, input_dto: MarkOutputReadInputDTO) -> AgentOutputDTO:
        output = await self.outputs.mark_read(
            input_dto.user_id, input_dto.output_id, self.clock.now()
        )
        if output is None:
            raise AgentOutputNotFoundError()
        return AgentOutputDTO.from_domain(output)
