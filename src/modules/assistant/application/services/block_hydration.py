"""Stored blocks → response blocks: draft references become current drafts.

History stores a draft's **id**, never its numbers, so every read shows the
draft as it is now (pending, confirmed with its movement, or discarded). A
reference whose draft vanished is dropped rather than invented.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import TypeAdapter

from src.modules.assistant.application.dto.blocks import (
    ApiBlock,
    DebtDraftBlock,
    DraftBlock,
)
from src.modules.assistant.application.dto.debt_draft import DebtDraftDTO
from src.modules.assistant.application.dto.draft import DraftDTO
from src.modules.assistant.domain.entities.debt_draft import DebtDraft
from src.modules.assistant.domain.entities.movement_draft import MovementDraft

_API_BLOCK: TypeAdapter[ApiBlock] = TypeAdapter(ApiBlock)


def draft_ids_in(blocks: Sequence[Mapping[str, Any]]) -> list[str]:
    return [str(block["draft_id"]) for block in blocks if block.get("type") == "draft"]


def debt_draft_ids_in(blocks: Sequence[Mapping[str, Any]]) -> list[str]:
    return [str(block["debt_draft_id"]) for block in blocks if block.get("type") == "debt_draft"]


def hydrate_blocks(
    blocks: Sequence[Mapping[str, Any]],
    drafts_by_id: Mapping[str, MovementDraft],
    debt_drafts_by_id: Mapping[str, DebtDraft] | None = None,
) -> list[ApiBlock]:
    debts = debt_drafts_by_id or {}
    hydrated: list[ApiBlock] = []
    for raw in blocks:
        if raw.get("type") == "draft":
            draft = drafts_by_id.get(str(raw.get("draft_id")))
            if draft is None:
                continue
            hydrated.append(DraftBlock(type="draft", draft=DraftDTO.from_domain(draft)))
        elif raw.get("type") == "debt_draft":
            debt_draft = debts.get(str(raw.get("debt_draft_id")))
            if debt_draft is None:
                continue
            hydrated.append(
                DebtDraftBlock(type="debt_draft", debt_draft=DebtDraftDTO.from_domain(debt_draft))
            )
        else:
            hydrated.append(_API_BLOCK.validate_python(dict(raw)))
    return hydrated
