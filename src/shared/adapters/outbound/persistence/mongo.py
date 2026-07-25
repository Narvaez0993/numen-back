from collections.abc import Iterable
from contextvars import ContextVar
from typing import Any

from beanie import Document, init_beanie
from pymongo import AsyncMongoClient
from pymongo.asynchronous.client_session import AsyncClientSession

from src.shared.adapters.outbound.config.settings import Settings

_client: AsyncMongoClient[Any] | None = None

# The transaction session in flight, if any. `MongoUnitOfWork` publishes it here
# and every repository reads it, so a use case can ask for atomicity without any
# layer above the adapters knowing that Mongo sessions exist.
_session: ContextVar[AsyncClientSession | None] = ContextVar("mongo_session", default=None)


def current_session() -> AsyncClientSession | None:
    """The active transaction session, or `None` outside a transaction.

    Repositories pass this to every write: pymongo treats `session=None` as "no
    transaction", so the same code path works both ways.
    """
    return _session.get()


def set_current_session(session: AsyncClientSession | None) -> Any:
    """For `MongoUnitOfWork` only. Returns the token to reset with."""
    return _session.set(session)


def reset_current_session(token: Any) -> None:
    """For `MongoUnitOfWork` only."""
    _session.reset(token)


def get_mongo_client(settings: Settings) -> AsyncMongoClient[Any]:
    """Return a singleton pymongo async client. Connection is lazy until first op."""
    global _client
    if _client is None:
        _client = AsyncMongoClient(
            settings.mongo_uri,
            uuidRepresentation="standard",
            tz_aware=True,
        )
    return _client


async def init_persistence(settings: Settings, documents: Iterable[type[Document]]) -> None:
    """Connect to Mongo and register Beanie documents.

    Call from FastAPI lifespan and from the ARQ worker startup.
    """
    client = get_mongo_client(settings)
    database = client[settings.mongo_db_name]
    await init_beanie(database=database, document_models=list(documents))


async def close_mongo_client() -> None:
    """Close the Mongo client. Call on FastAPI shutdown."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
