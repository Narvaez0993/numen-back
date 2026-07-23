from collections.abc import Iterable
from typing import Any

from beanie import Document, init_beanie
from pymongo import AsyncMongoClient

from src.shared.adapters.outbound.config.settings import Settings

_client: AsyncMongoClient[Any] | None = None


def get_mongo_client(settings: Settings) -> AsyncMongoClient[Any]:
    """Return a singleton pymongo async client. Connection is lazy until first op."""
    global _client
    if _client is None:
        _client = AsyncMongoClient(settings.mongo_uri, uuidRepresentation="standard")
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


# Note: `with_transaction` helper for Mongo multi-document transactions
# will be added when the first module needs it (expenses + accounts cash-basis flow).
# Requires the cluster to be a replica set (configured in docker-compose).
