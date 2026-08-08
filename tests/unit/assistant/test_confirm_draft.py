"""Confirming and discarding: the only two exits of a pending draft."""

import pytest

from src.modules.assistant.application.dto.draft_commands import (
    ConfirmDraftInputDTO,
    DiscardDraftInputDTO,
)
from src.modules.assistant.application.use_cases.confirm_draft import ConfirmDraftUseCase
from src.modules.assistant.application.use_cases.discard_draft import DiscardDraftUseCase
from src.modules.assistant.domain.errors import (
    DraftNotFoundError,
    DraftNotPendingError,
    DraftSourceRequiredError,
)

from .fakes import CARD_ID, USER_ID, FakeDrafts, FakeMovementRecorder, draft


def confirm_input(draft_id: str, **overrides: object) -> ConfirmDraftInputDTO:
    return ConfirmDraftInputDTO(user_id=USER_ID, draft_id=draft_id, **overrides)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_confirm_records_through_movements_with_the_draft_as_idempotency_key() -> None:
    staged = draft()
    drafts = FakeDrafts([staged])
    recorder = FakeMovementRecorder()
    case = ConfirmDraftUseCase(drafts=drafts, movement_recorder=recorder)

    output = await case.execute(confirm_input(staged.id))

    assert recorder.recorded[0]["idempotency_key"] == staged.id
    assert recorder.recorded[0]["amount"] == staged.amount
    assert output.draft.status == "confirmed"
    assert output.movement_id == "mov-1"
    assert drafts.by_id[staged.id].movement_id == "mov-1"


@pytest.mark.asyncio
async def test_overrides_from_the_edit_form_win_over_what_the_agent_staged() -> None:
    staged = draft()
    drafts = FakeDrafts([staged])
    recorder = FakeMovementRecorder()
    case = ConfirmDraftUseCase(drafts=drafts, movement_recorder=recorder)

    output = await case.execute(
        confirm_input(staged.id, amount=30_000, description="Cena con Sofi")
    )

    assert recorder.recorded[0]["amount"] == 30_000
    assert recorder.recorded[0]["description"] == "Cena con Sofi"
    assert output.draft.amount == 30_000


@pytest.mark.asyncio
async def test_a_draft_without_a_source_cannot_be_confirmed() -> None:
    """A draft may not know where the money came from; a movement never may."""
    staged = draft(source_id=None, source_type=None)
    drafts = FakeDrafts([staged])
    recorder = FakeMovementRecorder()
    case = ConfirmDraftUseCase(drafts=drafts, movement_recorder=recorder)

    with pytest.raises(DraftSourceRequiredError):
        await case.execute(confirm_input(staged.id))

    assert recorder.recorded == []
    assert drafts.by_id[staged.id].status == "pending"


@pytest.mark.asyncio
async def test_the_card_answers_the_missing_source_as_an_override() -> None:
    """What the picker sends is an ordinary override — no second endpoint."""
    staged = draft(source_id=None, source_type=None)
    drafts = FakeDrafts([staged])
    recorder = FakeMovementRecorder()
    case = ConfirmDraftUseCase(drafts=drafts, movement_recorder=recorder)

    output = await case.execute(
        confirm_input(staged.id, source_id=CARD_ID, source_type="credit_card")
    )

    assert recorder.recorded[0]["source_id"] == CARD_ID
    assert recorder.recorded[0]["source_type"] == "credit_card"
    assert output.draft.status == "confirmed"


@pytest.mark.asyncio
async def test_category_none_means_keep_unless_explicitly_cleared() -> None:
    staged = draft()
    drafts = FakeDrafts([staged])
    recorder = FakeMovementRecorder()
    case = ConfirmDraftUseCase(drafts=drafts, movement_recorder=recorder)

    await case.execute(confirm_input(staged.id))
    assert recorder.recorded[0]["category_id"] == staged.category_id

    second = draft()
    await FakeDrafts([second]).save(second)  # fresh store for the cleared variant
    drafts_two = FakeDrafts([second])
    case_two = ConfirmDraftUseCase(drafts=drafts_two, movement_recorder=recorder)
    await case_two.execute(confirm_input(second.id, clear_category=True))
    assert recorder.recorded[1]["category_id"] is None


@pytest.mark.asyncio
async def test_a_late_confirm_is_a_conflict() -> None:
    staged = draft().discard()
    case = ConfirmDraftUseCase(
        drafts=FakeDrafts([staged]), movement_recorder=FakeMovementRecorder()
    )
    with pytest.raises(DraftNotPendingError):
        await case.execute(confirm_input(staged.id))


@pytest.mark.asyncio
async def test_a_missing_draft_is_a_404() -> None:
    case = ConfirmDraftUseCase(drafts=FakeDrafts(), movement_recorder=FakeMovementRecorder())
    with pytest.raises(DraftNotFoundError):
        await case.execute(confirm_input("nope"))


@pytest.mark.asyncio
async def test_discard_flips_the_status_and_touches_no_money() -> None:
    staged = draft()
    drafts = FakeDrafts([staged])
    case = DiscardDraftUseCase(drafts=drafts)

    output = await case.execute(DiscardDraftInputDTO(user_id=USER_ID, draft_id=staged.id))

    assert output.draft.status == "discarded"
    assert drafts.by_id[staged.id].status == "discarded"


@pytest.mark.asyncio
async def test_confirm_forwards_the_drafts_provenance() -> None:
    spoken = draft(captured_via="voice")
    recorder = FakeMovementRecorder()
    case = ConfirmDraftUseCase(drafts=FakeDrafts([spoken]), movement_recorder=recorder)

    await case.execute(confirm_input(spoken.id))

    assert recorder.recorded[0]["captured_via"] == "voice"
