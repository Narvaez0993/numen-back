"""ARQ worker entry point.

Run with: `uv run arq src.core.workers.WorkerSettings`

When modules expose async jobs, register their functions in `WorkerSettings.functions`
and their cron schedules in `WorkerSettings.cron_jobs`. Initial setup has no jobs;
this file exists so the worker container can boot cleanly.
"""
from typing import Any, ClassVar

from arq.connections import RedisSettings

from src.core.di.container import get_container
from src.modules.auth.adapters.outbound.persistence.documents.user_document import UserDocument
from src.shared.adapters.outbound.config.settings import get_settings
from src.shared.adapters.outbound.logging.setup import configure_logging
from src.shared.adapters.outbound.persistence.mongo import close_mongo_client, init_persistence

_DOCUMENTS = [
    UserDocument,
]


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    await init_persistence(settings, _DOCUMENTS)
    ctx["container"] = get_container()


async def shutdown(_ctx: dict[str, Any]) -> None:
    await close_mongo_client()


def _redis_settings_from_url(url: str) -> RedisSettings:
    return RedisSettings.from_dsn(url)


class WorkerSettings:
    """ARQ worker config. Add functions + cron jobs as modules expose them."""

    functions: ClassVar[list[Any]] = []
    cron_jobs: ClassVar[list[Any]] = []
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings_from_url(get_settings().redis_url)
