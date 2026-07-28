"""Confirming a draft is when the movement becomes real — through the same use
case the manual form uses, with the draft id as the idempotency key: a double
tap converges on one movement, a late tap on an already-settled draft is a 409.
"""

from dataclasses import dataclass

from src.modules.assistant.application.dto.draft import DraftDTO
from src.modules.assistant.application.dto.draft_commands import (
    ConfirmDraftInputDTO,
    ConfirmDraftOutputDTO,
)
from src.modules.assistant.application.ports.draft_repository import DraftRepository
from src.modules.assistant.application.ports.movement_recorder import MovementRecorder
from src.modules.assistant.domain.errors import DraftNotFoundError

_OVERRIDABLE = (
    "type",
    "description",
    "amount",
    "source_type",
    "source_id",
    "destination_type",
    "destination_id",
    "occurred_on",
)


@dataclass
class ConfirmDraftUseCase:
    drafts: DraftRepository
    movement_recorder: MovementRecorder

    async def execute(self, input_dto: ConfirmDraftInputDTO) -> ConfirmDraftOutputDTO:
        draft = await self.drafts.find(input_dto.user_id, input_dto.draft_id)
        if draft is None:
            raise DraftNotFoundError()

        edited = draft.apply_overrides(_overrides_from(input_dto))
        recorded = await self.movement_recorder.record(
            user_id=edited.user_id,
            currency=edited.currency,
            type=edited.type,
            description=edited.description,
            amount=edited.amount,
            source_type=edited.source_type,
            source_id=edited.source_id,
            destination_type=edited.destination_type,
            destination_id=edited.destination_id,
            category_id=edited.category_id,
            occurred_on=edited.occurred_on,
            idempotency_key=edited.id,
        )
        confirmed = edited.confirm(recorded.movement_id)
        await self.drafts.save(confirmed)
        return ConfirmDraftOutputDTO(
            draft=DraftDTO.from_domain(confirmed), movement_id=recorded.movement_id
        )


def _overrides_from(input_dto: ConfirmDraftInputDTO) -> dict[str, object]:
    """`None` means "keep what the agent staged"; the category also has an
    explicit clear flag because `None` cannot mean two things."""
    overrides: dict[str, object] = {
        name: value for name in _OVERRIDABLE if (value := getattr(input_dto, name)) is not None
    }
    if input_dto.clear_category:
        overrides["category_id"] = None
    elif input_dto.category_id is not None:
        overrides["category_id"] = input_dto.category_id
    return overrides
