"""The weekly review's Monday sweep, as an inbound adapter driven by the clock.

Runs Mondays at 07:00 UTC over the ISO week that just closed. Idempotent by
the same unique index the Corte uses, so `run_at_startup` backfills safely.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def run_weekly_reviews(ctx: dict[str, Any]) -> dict[str, int]:
    """ARQ entry point. `ctx["container"]` is wired in `workers.startup`."""
    container = ctx["container"]

    counts: dict[str, int] = await container.run_weekly_reviews_use_case.execute()

    logger.info("weekly_reviews_run", extra=counts)
    return counts
