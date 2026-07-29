from dataclasses import dataclass

from src.modules.assistant.application.dto.draft import DraftDTO
from src.modules.assistant.application.dto.draft_commands import (
    DiscardDraftInputDTO,
    DiscardDraftOutputDTO,
)
from src.modules.assistant.application.ports.draft_repository import DraftRepository
from src.modules.assistant.domain.errors import DraftNotFoundError


@dataclass
class DiscardDraftUseCase:
    """Discarding never touches the ledger — the draft only ever existed in chat."""

    drafts: DraftRepository

    async def execute(self, input_dto: DiscardDraftInputDTO) -> DiscardDraftOutputDTO:
        draft = await self.drafts.find(input_dto.user_id, input_dto.draft_id)
        if draft is None:
            raise DraftNotFoundError()
        discarded = draft.discard()
        await self.drafts.save(discarded)
        return DiscardDraftOutputDTO(draft=DraftDTO.from_domain(discarded))
