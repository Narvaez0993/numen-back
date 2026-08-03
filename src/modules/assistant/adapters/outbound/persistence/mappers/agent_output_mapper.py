from typing import Any
from uuid import UUID

from src.modules.assistant.adapters.outbound.persistence.documents.agent_output_document import (
    AgentOutputDocument,
)
from src.modules.assistant.domain.entities.agent_output import AgentOutput, Play

_LIFECYCLE = ("id", "action", "text", "status", "result_id", "failure_code", "applied_at")


class AgentOutputMapper:
    @staticmethod
    def to_domain(doc: AgentOutputDocument) -> AgentOutput:
        return AgentOutput(
            id=doc.id,
            user_id=UUID(doc.user_id),
            kind=doc.kind,
            period=doc.period,
            payload=doc.payload,
            plays=tuple(_play_from(raw) for raw in doc.plays),
            created_at=doc.created_at,
            read_at=doc.read_at,
            dismissed_at=doc.dismissed_at,
        )

    @staticmethod
    def to_document(output: AgentOutput) -> AgentOutputDocument:
        return AgentOutputDocument(
            id=output.id,
            user_id=str(output.user_id),
            kind=output.kind,
            period=output.period,
            payload=dict(output.payload),
            plays=[_play_to(play) for play in output.plays],
            created_at=output.created_at,
            read_at=output.read_at,
            dismissed_at=output.dismissed_at,
        )


def _play_from(raw: dict[str, Any]) -> Play:
    return Play(
        id=str(raw["id"]),
        action=str(raw["action"]),
        params={k: v for k, v in raw.items() if k not in _LIFECYCLE},
        text=str(raw.get("text", "")),
        status=str(raw["status"]),
        result_id=raw.get("result_id"),
        failure_code=raw.get("failure_code"),
        applied_at=raw.get("applied_at"),
    )


def _play_to(play: Play) -> dict[str, Any]:
    return {
        "id": play.id,
        "action": play.action,
        "text": play.text,
        "status": play.status,
        "result_id": play.result_id,
        "failure_code": play.failure_code,
        "applied_at": play.applied_at,
        **dict(play.params),
    }
