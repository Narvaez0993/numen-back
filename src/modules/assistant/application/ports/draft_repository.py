from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.assistant.domain.entities.movement_draft import MovementDraft


class DraftRepository(Protocol):
    async def save(self, draft: MovementDraft) -> None: ...

    async def save_many(self, drafts: Sequence[MovementDraft]) -> None: ...

    async def find(self, user_id: UUID, draft_id: str) -> MovementDraft | None: ...

    async def find_many(
        self, user_id: UUID, draft_ids: Sequence[str]
    ) -> tuple[MovementDraft, ...]: ...
