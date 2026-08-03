"""Outbound port: the agent's proactive deliverables.

`transition_play` is deliberately stronger than the draft repo's load-then-save:
plays move real money on apply, so every transition is one conditional Mongo
write — `None` back means the precondition (current status) no longer held.
"""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.assistant.domain.entities.agent_output import AgentOutput


class AgentOutputAlreadyExistsError(Exception):
    """The unique `(user, kind, period)` index fired — a re-run skips, never fails."""


class AgentOutputRepository(Protocol):
    async def add(self, output: AgentOutput) -> None: ...

    async def find(self, user_id: UUID, output_id: str) -> AgentOutput | None: ...

    async def find_by_period(self, user_id: UUID, kind: str, period: str) -> AgentOutput | None: ...

    async def latest(self, user_id: UUID, kind: str, limit: int) -> tuple[AgentOutput, ...]: ...

    async def mark_read(self, user_id: UUID, output_id: str, at: datetime) -> AgentOutput | None:
        """Sets `read_at` only when it is still null; returns the current state."""
        ...

    async def dismiss(self, user_id: UUID, output_id: str, at: datetime) -> AgentOutput | None: ...

    async def transition_play(
        self,
        user_id: UUID,
        output_id: str,
        play_id: str,
        *,
        from_status: str,
        to_status: str,
        result_id: str | None = None,
        failure_code: str | None = None,
        applied_at: datetime | None = None,
    ) -> AgentOutput | None: ...
