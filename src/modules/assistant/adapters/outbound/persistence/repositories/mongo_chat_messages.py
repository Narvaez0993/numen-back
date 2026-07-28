from uuid import UUID

from pymongo.errors import DuplicateKeyError

from src.modules.assistant.adapters.outbound.persistence.documents.chat_message_document import (
    ChatMessageDocument,
)
from src.modules.assistant.adapters.outbound.persistence.mappers.chat_message_mapper import (
    ChatMessageMapper,
)
from src.modules.assistant.application.ports.chat_message_repository import StoredChatMessage
from src.modules.assistant.domain.errors import DuplicateMessageError
from src.shared.adapters.outbound.persistence.mongo import current_session


class MongoChatMessageRepository:
    """Beanie/Mongo implementation of `ChatMessageRepository`.

    Pages walk `created_at` backwards and are returned chronological — the shape
    a chat renders in. The unique `(user, client_message_id)` index backs the
    duplicate check against the race the pre-read cannot see.
    """

    async def append(self, message: StoredChatMessage) -> None:
        try:
            await ChatMessageMapper.to_document(message).insert(session=current_session())
        except DuplicateKeyError as exc:
            raise DuplicateMessageError() from exc

    async def recent(self, user_id: UUID, limit: int) -> tuple[StoredChatMessage, ...]:
        docs = (
            await ChatMessageDocument.find({"user_id": str(user_id)})
            .sort("-created_at")
            .limit(limit)
            .to_list()
        )
        return tuple(ChatMessageMapper.to_stored(doc) for doc in reversed(docs))

    async def before(
        self, user_id: UUID, before_id: str | None, limit: int
    ) -> tuple[StoredChatMessage, ...]:
        criteria: dict[str, object] = {"user_id": str(user_id)}
        if before_id is not None:
            anchor = await ChatMessageDocument.find_one(
                ChatMessageDocument.id == before_id,
                ChatMessageDocument.user_id == str(user_id),
            )
            if anchor is None:
                return ()
            criteria["created_at"] = {"$lt": anchor.created_at}
        docs = await ChatMessageDocument.find(criteria).sort("-created_at").limit(limit).to_list()
        return tuple(ChatMessageMapper.to_stored(doc) for doc in reversed(docs))

    async def find_by_client_id(
        self, user_id: UUID, client_message_id: str
    ) -> StoredChatMessage | None:
        doc = await ChatMessageDocument.find_one(
            ChatMessageDocument.user_id == str(user_id),
            ChatMessageDocument.client_message_id == client_message_id,
        )
        return ChatMessageMapper.to_stored(doc) if doc else None
