"""Integration fixtures: a real MongoDB (replica set, so transactions work).

Point `MONGO_TEST_URI` at one, e.g.
`mongodb://localhost:27017/?replicaSet=rs0&directConnection=true`
(`docker compose -f docker/docker-compose.yml up -d mongo`). Without it every test
here is skipped, so a plain `uv run pytest` still passes on a machine without Docker.

Each pytest session works in its own database (unique name) and drops it at the end;
each test starts from empty collections.
"""

import os
import uuid
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
import pytest_asyncio
from beanie import init_beanie
from pymongo import AsyncMongoClient, MongoClient

from src.modules.accounts.adapters.outbound.persistence.documents.account_document import (
    AccountDocument,
)
from src.modules.accounts.adapters.outbound.persistence.documents.credit_card_document import (
    CreditCardDocument,
)
from src.modules.movements.adapters.outbound.persistence.documents.idempotency_key_document import (
    IdempotencyKeyDocument,
)
from src.modules.movements.adapters.outbound.persistence.documents.movement_document import (
    MovementDocument,
)

MONGO_TEST_URI = os.environ.get("MONGO_TEST_URI")
SKIP_REASON = (
    "MONGO_TEST_URI is not set: integration tests need a MongoDB replica set "
    "(e.g. mongodb://localhost:27017/?replicaSet=rs0&directConnection=true)"
)
DOCUMENTS: list[Any] = [
    AccountDocument,
    CreditCardDocument,
    MovementDocument,
    IdempotencyKeyDocument,
]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/integration" not in item.nodeid.replace("\\", "/"):
            continue
        item.add_marker(pytest.mark.integration)
        if not MONGO_TEST_URI:
            item.add_marker(pytest.mark.skip(reason=SKIP_REASON))


@pytest.fixture(scope="session")
def mongo_db_name() -> Iterator[str]:
    """A database name unique to this run; dropped when the session ends."""
    name = f"numen_it_{uuid.uuid4().hex[:12]}"
    yield name
    if MONGO_TEST_URI:
        client: MongoClient[Any] = MongoClient(MONGO_TEST_URI)
        try:
            client.drop_database(name)
        finally:
            client.close()


@pytest_asyncio.fixture
async def mongo_client(mongo_db_name: str) -> AsyncIterator[AsyncMongoClient[Any]]:
    """Beanie initialised on the session database, with every collection emptied."""
    assert MONGO_TEST_URI
    client: AsyncMongoClient[Any] = AsyncMongoClient(
        MONGO_TEST_URI, uuidRepresentation="standard", tz_aware=True
    )
    await init_beanie(database=client[mongo_db_name], document_models=DOCUMENTS)
    for document in DOCUMENTS:
        await document.get_pymongo_collection().delete_many({})
    try:
        yield client
    finally:
        await client.close()
