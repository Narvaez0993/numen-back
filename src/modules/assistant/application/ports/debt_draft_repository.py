from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.modules.assistant.domain.entities.debt_draft import DebtDraft


class DebtDraftRepository(Protocol):
    """Its own store, mirroring `DraftRepository`. Two collections rather than one
    polymorphic table: the two drafts share a lifecycle and nothing else, and a
    single collection would mean every read filtering on a discriminator."""

    async def save(self, draft: DebtDraft) -> None: ...

    async def save_many(self, drafts: Sequence[DebtDraft]) -> None: ...

    async def find(self, user_id: UUID, draft_id: str) -> DebtDraft | None: ...

    async def find_many(self, user_id: UUID, draft_ids: Sequence[str]) -> tuple[DebtDraft, ...]: ...
