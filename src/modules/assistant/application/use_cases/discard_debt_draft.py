from dataclasses import dataclass

from src.modules.assistant.application.dto.debt_draft import DebtDraftDTO
from src.modules.assistant.application.dto.debt_draft_commands import (
    DiscardDebtDraftInputDTO,
    DiscardDebtDraftOutputDTO,
)
from src.modules.assistant.application.ports.debt_draft_repository import DebtDraftRepository
from src.modules.assistant.domain.errors import DraftNotFoundError


@dataclass
class DiscardDebtDraftUseCase:
    """Discarding never touches the ledger — the draft only ever existed in chat."""

    debt_drafts: DebtDraftRepository

    async def execute(self, input_dto: DiscardDebtDraftInputDTO) -> DiscardDebtDraftOutputDTO:
        draft = await self.debt_drafts.find(input_dto.user_id, input_dto.draft_id)
        if draft is None:
            raise DraftNotFoundError()
        discarded = draft.discard()
        await self.debt_drafts.save(discarded)
        return DiscardDebtDraftOutputDTO(draft=DebtDraftDTO.from_domain(discarded))
