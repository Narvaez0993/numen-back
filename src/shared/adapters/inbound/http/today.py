"""The caller's local day, for endpoints whose answer depends on "today".

Second module to need it (Home, and now subscriptions), so it lives here instead of
being copied: without it, "spent today", "days left" and "what gets charged today"
are off by a few hours a day for anyone far from UTC — and the app is global-first.
It also makes those endpoints deterministic in tests.
"""

from datetime import UTC, datetime

from src.shared.domain.errors import ValidationError


def resolve_today(raw: str | None) -> str:
    """`YYYY-MM-DD` from the query, or the server's UTC date when absent."""
    if raw is None:
        return datetime.now(UTC).date().isoformat()
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValidationError(f"Invalid date: {raw} (expected YYYY-MM-DD)") from exc
