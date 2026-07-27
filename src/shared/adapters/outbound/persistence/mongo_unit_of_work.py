from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from pymongo import AsyncMongoClient
from pymongo.asynchronous.client_session import AsyncClientSession

from src.shared.adapters.outbound.persistence.mongo import (
    current_session,
    reset_current_session,
    set_current_session,
)

T = TypeVar("T")


class MongoUnitOfWork:
    """`UnitOfWork` over a Mongo multi-document transaction.

    Uses `session.with_transaction`, which commits on success, aborts on error and
    **retries transient failures** (elections, write conflicts). The session is
    published in a ContextVar for the duration, so repositories enlist in it
    without the application layer ever seeing a session.

    **Re-entrant**: when a transaction is already running, `atomic` joins it instead
    of opening a second session (Mongo has no nested transactions). That is what lets
    one use case compose another that is atomic on its own — a subscription charge
    marking itself settled *and* registering its movement in the same all-or-nothing
    write, without either side knowing about the other.

    Requires a replica set (configured in `docker/docker-compose.yml`). Collections
    must already exist when a transaction runs — they do, because
    `init_persistence` registers every document at startup.
    """

    def __init__(self, client: AsyncMongoClient[Any]) -> None:
        self._client = client

    async def atomic(self, operation: Callable[[], Awaitable[T]]) -> T:
        if current_session() is not None:
            # Already inside a transaction: the outermost one owns commit/abort, so
            # joining it keeps this operation part of the same unit.
            return await operation()

        async with self._client.start_session() as session:

            async def run(active: AsyncClientSession) -> T:
                token = set_current_session(active)
                try:
                    return await operation()
                finally:
                    reset_current_session(token)

            return await session.with_transaction(run)
