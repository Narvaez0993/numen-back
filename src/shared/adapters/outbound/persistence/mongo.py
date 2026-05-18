from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from beanie import Document, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from src.shared.adapters.outbound.config.settings import Settings

_client: AsyncIOMotorClient[Any] | None = None


def get_mongo_client(settings: Settings) -> AsyncIOMotorClient[Any]:
    """Return a singleton Motor client. Connection is lazy until first op."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri, uuidRepresentation="standard")
    return _client


async def init_persistence(settings: Settings, documents: Iterable[type[Document]]) -> None:
    """Connect to Mongo and register Beanie documents.

    Call from FastAPI lifespan and from the ARQ worker startup.
    """
    client = get_mongo_client(settings)
    database = client[settings.mongo_db_name]
    await init_beanie(database=database, document_models=list(documents))  # type: ignore[arg-type]


async def close_mongo_client() -> None:
    """Close the Motor client. Call on FastAPI shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def with_transaction[T](
    settings: Settings,
    operation: Callable[[Any], Awaitable[T]],
) -> T:
    """Run `operation` inside a Mongo multi-document transaction.

    Requires the cluster to be a replica set (see docker-compose).
    """
    client = get_mongo_client(settings)
    session = await client.start_session()
    async with session, session.start_transaction():
        return await operation(session)
