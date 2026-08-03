"""El Corte's monthly sweep, as an inbound adapter driven by the clock.

Runs the 1st at 06:00 UTC over every user's just-closed month. Generation is
idempotent (unique index per user/kind/period + skip), so `run_at_startup`
doubles as the backfill after a deploy or an outage without double-writing.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def run_monthly_summaries(ctx: dict[str, Any]) -> dict[str, int]:
    """ARQ entry point. `ctx["container"]` is wired in `workers.startup`."""
    container = ctx["container"]

    counts: dict[str, int] = await container.run_monthly_summaries_use_case.execute()

    logger.info("monthly_summaries_run", extra=counts)
    return counts
