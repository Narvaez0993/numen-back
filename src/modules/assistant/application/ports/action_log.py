"""Outbound port: the cost ledger — one row per model action, failed ones too.

The margin only closes with small models + caching + batching (docs 07); this
log is how we know instead of hope. Best-effort by design: it records after the
turn's commit and a lost row costs analytics, never money or history.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ActionLogEntry:
    user_id: UUID
    action: str
    """`chat` for now; `parse_voice`/`parse_photo`/proactive kinds come later."""
    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float
    period: str
    failed: bool


class ActionLog(Protocol):
    async def record(self, entry: ActionLogEntry) -> None: ...
