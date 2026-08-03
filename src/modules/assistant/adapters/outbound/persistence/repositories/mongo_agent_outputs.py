from datetime import datetime
from typing import Any
from uuid import UUID

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from src.modules.assistant.adapters.outbound.persistence.documents.agent_output_document import (
    AgentOutputDocument,
)
from src.modules.assistant.adapters.outbound.persistence.mappers.agent_output_mapper import (
    AgentOutputMapper,
)
from src.modules.assistant.application.ports.agent_output_repository import (
    AgentOutputAlreadyExistsError,
)
from src.modules.assistant.domain.entities.agent_output import AgentOutput


class MongoAgentOutputs:
    """Beanie/Mongo implementation of `AgentOutputRepository`.

    Deliberately stronger than the draft repo's load-then-save: plays move real
    money, so every state change is one conditional `find_one_and_update` —
    the `$elemMatch` (id AND current status) is what makes the positional `$`
    point at the right element and the double-tap lose the race cleanly.
    """

    async def add(self, output: AgentOutput) -> None:
        try:
            await AgentOutputMapper.to_document(output).insert()
        except DuplicateKeyError as exc:
            raise AgentOutputAlreadyExistsError() from exc

    async def find(self, user_id: UUID, output_id: str) -> AgentOutput | None:
        doc = await AgentOutputDocument.find_one(
            AgentOutputDocument.id == output_id,
            AgentOutputDocument.user_id == str(user_id),
        )
        return AgentOutputMapper.to_domain(doc) if doc else None

    async def find_by_period(self, user_id: UUID, kind: str, period: str) -> AgentOutput | None:
        doc = await AgentOutputDocument.find_one(
            AgentOutputDocument.user_id == str(user_id),
            AgentOutputDocument.kind == kind,
            AgentOutputDocument.period == period,
        )
        return AgentOutputMapper.to_domain(doc) if doc else None

    async def latest(self, user_id: UUID, kind: str, limit: int) -> tuple[AgentOutput, ...]:
        docs = (
            await AgentOutputDocument.find(
                AgentOutputDocument.user_id == str(user_id),
                AgentOutputDocument.kind == kind,
            )
            .sort("-created_at")
            .limit(limit)
            .to_list()
        )
        return tuple(AgentOutputMapper.to_domain(doc) for doc in docs)

    async def mark_read(self, user_id: UUID, output_id: str, at: datetime) -> AgentOutput | None:
        collection = AgentOutputDocument.get_pymongo_collection()
        await collection.update_one(
            {"_id": output_id, "user_id": str(user_id), "read_at": None},
            {"$set": {"read_at": at}},
        )
        return await self.find(user_id, output_id)

    async def dismiss(self, user_id: UUID, output_id: str, at: datetime) -> AgentOutput | None:
        collection = AgentOutputDocument.get_pymongo_collection()
        await collection.update_one(
            {"_id": output_id, "user_id": str(user_id), "dismissed_at": None},
            {"$set": {"dismissed_at": at}},
        )
        return await self.find(user_id, output_id)

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
    ) -> AgentOutput | None:
        updates: dict[str, Any] = {"plays.$.status": to_status}
        if result_id is not None:
            updates["plays.$.result_id"] = result_id
        if failure_code is not None:
            updates["plays.$.failure_code"] = failure_code
        if applied_at is not None:
            updates["plays.$.applied_at"] = applied_at
        collection = AgentOutputDocument.get_pymongo_collection()
        raw = await collection.find_one_and_update(
            {
                "_id": output_id,
                "user_id": str(user_id),
                "plays": {"$elemMatch": {"id": play_id, "status": from_status}},
            },
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
        if raw is None:
            return None
        # Raw pymongo dict (`_id`), not a Beanie document — normalize by hand.
        raw["id"] = str(raw.pop("_id"))
        return AgentOutputMapper.to_domain(AgentOutputDocument.model_validate(raw))
