from uuid import UUID

from pymongo.errors import DuplicateKeyError

from src.modules.movements.adapters.outbound.persistence.documents.idempotency_key_document import (
    IdempotencyKeyDocument,
)
from src.modules.movements.application.ports.idempotency_store import (
    IdempotencyConflictError,
)
from src.shared.adapters.outbound.persistence.mongo import current_session


class MongoIdempotencyStore:
    """`IdempotencyStore` over a TTL collection with a unique `(user_id, key)`.

    `reserve` leans on the unique index instead of a check-then-write: two
    concurrent requests with the same key both try to insert, one wins, the other
    gets a duplicate error and replays the winner's movement.
    """

    async def find(self, user_id: UUID, key: str) -> str | None:
        doc = await IdempotencyKeyDocument.find_one(
            IdempotencyKeyDocument.user_id == str(user_id),
            IdempotencyKeyDocument.key == key,
        )
        return doc.movement_id if doc else None

    async def reserve(self, user_id: UUID, key: str, movement_id: str) -> None:
        record = IdempotencyKeyDocument(user_id=str(user_id), key=key, movement_id=movement_id)
        try:
            await record.insert(session=current_session())
        except DuplicateKeyError as exc:
            raise IdempotencyConflictError(key) from exc
