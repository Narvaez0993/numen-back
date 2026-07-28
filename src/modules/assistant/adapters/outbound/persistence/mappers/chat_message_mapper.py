from uuid import UUID

from src.modules.assistant.adapters.outbound.persistence.documents.chat_message_document import (
    ChatMessageDocument,
)
from src.modules.assistant.application.ports.chat_message_repository import StoredChatMessage


class ChatMessageMapper:
    @staticmethod
    def to_stored(doc: ChatMessageDocument) -> StoredChatMessage:
        return StoredChatMessage(
            id=doc.id,
            user_id=UUID(doc.user_id),
            role=doc.role,
            blocks=tuple(doc.blocks),
            client_message_id=doc.client_message_id,
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(message: StoredChatMessage) -> ChatMessageDocument:
        return ChatMessageDocument(
            id=message.id,
            user_id=str(message.user_id),
            role=message.role,
            blocks=[dict(block) for block in message.blocks],
            client_message_id=message.client_message_id,
            created_at=message.created_at,
        )
