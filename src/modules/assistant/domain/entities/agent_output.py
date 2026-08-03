"""What the agent produced without being asked — a Corte, a weekly review.

The payload is a frozen snapshot: a month's story never changes after it is
told. The only living part is each play's status — and those transitions are
guarded by the repository's conditional update, not re-modelled here (one
Mongo document, one atomic write; two sources of truth would drift).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

MONTHLY_SUMMARY = "monthly_summary"
WEEKLY_REVIEW = "weekly_review"

PLAY_PROPOSED = "proposed"
PLAY_APPLYING = "applying"
PLAY_APPLIED = "applied"
PLAY_FAILED = "failed"

APPLYABLE_ACTIONS = frozenset(
    {"set_category_cap", "raise_category_cap", "set_month_cap", "contribute_goal"}
)


@dataclass(frozen=True)
class Play:
    """One move the agent proposed. `treat` is advice, not a button."""

    id: str
    action: str
    params: Mapping[str, Any]
    """Action-specific fields, validated against `plays.py` at composition."""
    text: str
    status: str
    result_id: str | None
    """What applying produced (a budget id); None for goal contributions."""
    failure_code: str | None
    applied_at: datetime | None

    @property
    def applyable(self) -> bool:
        return self.action in APPLYABLE_ACTIONS


@dataclass(frozen=True)
class AgentOutput:
    id: str
    user_id: UUID
    kind: str
    period: str
    """`YYYY-MM` for a Corte, `YYYY-Www` (ISO week) for a weekly review."""
    payload: Mapping[str, Any]
    plays: tuple[Play, ...]
    created_at: datetime
    read_at: datetime | None
    dismissed_at: datetime | None

    def play(self, play_id: str) -> Play | None:
        return next((p for p in self.plays if p.id == play_id), None)
