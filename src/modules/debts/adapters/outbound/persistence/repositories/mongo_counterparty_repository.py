from uuid import UUID

from src.modules.debts.adapters.outbound.persistence.documents.counterparty_document import (
    CounterpartyDocument,
)
from src.modules.debts.adapters.outbound.persistence.mappers.counterparty_mapper import (
    CounterpartyMapper,
)
from src.modules.debts.domain.entities.counterparty import Counterparty, name_key
from src.shared.adapters.outbound.persistence.mongo import current_session


class MongoCounterpartyRepository:
    """Beanie/Mongo implementation of `CounterpartyRepository`.

    `find_by_name` runs on the stored `name_key`, the same normalization the unique
    index enforces — the lookup and the constraint cannot drift apart.
    """

    async def list_by_user(self, user_id: UUID) -> list[Counterparty]:
        docs = await CounterpartyDocument.find({"user_id": str(user_id)}).to_list()
        return [CounterpartyMapper.to_domain(doc) for doc in docs]

    async def find(self, user_id: UUID, counterparty_id: str) -> Counterparty | None:
        doc = await CounterpartyDocument.find_one(
            CounterpartyDocument.id == counterparty_id,
            CounterpartyDocument.user_id == str(user_id),
        )
        return CounterpartyMapper.to_domain(doc) if doc else None

    async def find_by_name(self, user_id: UUID, name: str) -> Counterparty | None:
        doc = await CounterpartyDocument.find_one(
            {"user_id": str(user_id), "name_key": name_key(name)}
        )
        return CounterpartyMapper.to_domain(doc) if doc else None

    async def save(self, counterparty: Counterparty) -> None:
        session = current_session()
        existing = await CounterpartyDocument.get(counterparty.id, session=session)
        if existing is None:
            await CounterpartyMapper.to_document(counterparty).insert(session=session)
            return
        fresh = CounterpartyMapper.to_document(counterparty)
        existing.name = fresh.name
        existing.name_key = fresh.name_key
        existing.color = fresh.color
        await existing.save(session=session)
