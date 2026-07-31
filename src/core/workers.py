"""ARQ worker entry point.

Run with: `uv run arq src.core.workers.WorkerSettings`

Jobs live with the module that owns them (`adapters/inbound/jobs/`), the same way a
router does: the clock is just another way in. This file only registers them.
"""

from typing import Any, ClassVar

from arq import cron
from arq.connections import RedisSettings

from src.core.di.container import get_container
from src.core.documents import ALL_DOCUMENTS
from src.modules.assistant.adapters.inbound.jobs.run_monthly_summaries import (
    run_monthly_summaries,
)
from src.modules.assistant.adapters.inbound.jobs.run_weekly_reviews import (
    run_weekly_reviews,
)
from src.modules.subscriptions.adapters.inbound.jobs.run_subscription_charges import (
    run_subscription_charges,
)
from src.shared.adapters.outbound.config.settings import get_settings
from src.shared.adapters.outbound.logging.setup import configure_logging
from src.shared.adapters.outbound.persistence.mongo import close_mongo_client, init_persistence


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    await init_persistence(settings, ALL_DOCUMENTS)
    ctx["container"] = get_container()


async def shutdown(_ctx: dict[str, Any]) -> None:
    await close_mongo_client()


async def heartbeat(_ctx: dict[str, Any]) -> str:
    """Liveness probe for the worker container."""
    return "ok"


def _redis_settings_from_url(url: str) -> RedisSettings:
    return RedisSettings.from_dsn(url)


class WorkerSettings:
    """ARQ worker config. Add functions + cron jobs as modules expose them."""

    functions: ClassVar[list[Any]] = [
        heartbeat,
        run_subscription_charges,
        run_monthly_summaries,
        run_weekly_reviews,
    ]
    cron_jobs: ClassVar[list[Any]] = [
        # Hourly: the confirmation window is measured in hours, so this is as
        # precise as the feature needs. `run_at_startup` picks up whatever came due
        # while the worker was down (bounded by CATCH_UP_DAYS).
        cron(run_subscription_charges, minute=0, run_at_startup=True),
        # The 1st at 06:00 UTC: last month just closed everywhere that matters.
        # `run_at_startup` doubles as the backfill after a deploy or an outage —
        # safe because generation is idempotent (unique index + skip).
        cron(
            run_monthly_summaries,
            day=1,
            hour=6,
            minute=0,
            timeout=1800,
            run_at_startup=True,
        ),
        # Mondays 07:00 UTC: the ISO week just closed everywhere that matters.
        cron(
            run_weekly_reviews,
            weekday="mon",
            hour=7,
            minute=0,
            timeout=1800,
            run_at_startup=True,
        ),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings_from_url(get_settings().redis_url)
