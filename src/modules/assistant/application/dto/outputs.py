from collections.abc import Mapping
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from src.modules.assistant.application.dto.plays import PlayDTO, play_dto_from_domain
from src.modules.assistant.domain.entities.agent_output import AgentOutput


class AgentOutputDTO(BaseModel):
    """An output as the client reads it. `payload` travels as composed — it was
    validated against the slide/weekly unions at generation and is immutable;
    the plays carry the only state that moves."""

    id: str
    kind: str
    period: str
    payload: Mapping[str, Any]
    plays: list[PlayDTO]
    created_at: datetime
    read_at: datetime | None
    dismissed_at: datetime | None

    @classmethod
    def from_domain(cls, output: AgentOutput) -> "AgentOutputDTO":
        return cls(
            id=output.id,
            kind=output.kind,
            period=output.period,
            payload=output.payload,
            plays=[play_dto_from_domain(play) for play in output.plays],
            created_at=output.created_at,
            read_at=output.read_at,
            dismissed_at=output.dismissed_at,
        )
