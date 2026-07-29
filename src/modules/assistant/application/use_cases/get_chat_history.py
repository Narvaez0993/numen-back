from dataclasses import dataclass

from src.modules.assistant.application.dto.chat import (
    ChatHistoryOutputDTO,
    ChatMessageDTO,
    HistoryInputDTO,
)
from src.modules.assistant.application.ports.chat_message_repository import ChatMessageRepository
from src.modules.assistant.application.ports.draft_repository import DraftRepository
from src.modules.assistant.application.services.block_hydration import (
    draft_ids_in,
    hydrate_blocks,
)

MAX_PAGE = 100


@dataclass
class GetChatHistoryUseCase:
    """A page of the single thread, drafts hydrated to their current state."""

    chat_messages: ChatMessageRepository
    drafts: DraftRepository

    async def execute(self, input_dto: HistoryInputDTO) -> ChatHistoryOutputDTO:
        limit = min(input_dto.limit, MAX_PAGE)
        page = await self.chat_messages.before(input_dto.user_id, input_dto.before, limit)

        wanted: list[str] = []
        for message in page:
            wanted.extend(draft_ids_in(message.blocks))
        drafts = await self.drafts.find_many(input_dto.user_id, wanted) if wanted else ()
        drafts_by_id = {draft.id: draft for draft in drafts}

        messages = [
            ChatMessageDTO(
                id=message.id,
                role=message.role,
                blocks=hydrate_blocks(message.blocks, drafts_by_id),
                created_at=message.created_at,
            )
            for message in page
        ]
        next_before = page[0].id if len(page) == limit else None
        return ChatHistoryOutputDTO(messages=messages, next_before=next_before)
