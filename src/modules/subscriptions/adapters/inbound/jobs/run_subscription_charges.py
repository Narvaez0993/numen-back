"""The recurring-charge engine, as an inbound adapter driven by the clock.

An hourly pass does two things, in order:

1. **open** a pending charge for everything due today, so the user gets asked;
2. **settle** the ones nobody answered within the confirmation window.

Hourly is enough: the window is measured in hours, and a charge opened at 00:10
settles on the 03:00 run. Both steps are idempotent, so a missed or repeated run
never charges twice.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def run_subscription_charges(ctx: dict[str, Any]) -> dict[str, int]:
    """ARQ entry point. `ctx["container"]` is wired in `workers.startup`."""
    container = ctx["container"]

    opened = await container.open_due_charges_use_case.execute()
    settled = await container.settle_unconfirmed_charges_use_case.execute()

    logger.info(
        "subscription_charges_run",
        extra={"opened": opened, "settled": settled},
    )
    return {"opened": opened, "settled": settled}
