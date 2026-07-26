"""ARQ worker entry point.

Run with: `uv run arq src.core.workers.WorkerSettings`

Jobs live with the module that owns them (`adapters/inbound/jobs/`), the same way a
router does: the clock is just another way in. This file only registers them.
"""

from typing import Any, ClassVar

from arq import cron
from arq.connections import RedisSettings

from src.core.di.container import get_container
from src.modules.accounts.adapters.outbound.persistence.documents.account_document import (
    AccountDocument,
)
from src.modules.accounts.adapters.outbound.persistence.documents.credit_card_document import (
    CreditCardDocument,
)
from src.modules.auth.adapters.outbound.persistence.documents.email_verification_code_document import (  # noqa: E501
    EmailVerificationCodeDocument,
)
from src.modules.auth.adapters.outbound.persistence.documents.refresh_token_document import (
    RefreshTokenDocument,
)
from src.modules.auth.adapters.outbound.persistence.documents.user_document import UserDocument
from src.modules.categories.adapters.outbound.persistence.documents.category_document import (
    CategoryDocument,
)
from src.modules.movements.adapters.outbound.persistence.documents.idempotency_key_document import (
    IdempotencyKeyDocument,
)
from src.modules.movements.adapters.outbound.persistence.documents.movement_document import (
    MovementDocument,
)
from src.modules.subscriptions.adapters.inbound.jobs.run_subscription_charges import (
    run_subscription_charges,
)
from src.modules.subscriptions.adapters.outbound.persistence.documents.subscription_charge_document import (  # noqa: E501
    SubscriptionChargeDocument,
)
from src.modules.subscriptions.adapters.outbound.persistence.documents.subscription_document import (  # noqa: E501
    SubscriptionDocument,
)
from src.shared.adapters.outbound.config.settings import get_settings
from src.shared.adapters.outbound.logging.setup import configure_logging
from src.shared.adapters.outbound.persistence.mongo import close_mongo_client, init_persistence

_DOCUMENTS = [
    UserDocument,
    EmailVerificationCodeDocument,
    RefreshTokenDocument,
    CategoryDocument,
    AccountDocument,
    CreditCardDocument,
    MovementDocument,
    IdempotencyKeyDocument,
    SubscriptionDocument,
    SubscriptionChargeDocument,
]


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    await init_persistence(settings, _DOCUMENTS)
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

    functions: ClassVar[list[Any]] = [heartbeat, run_subscription_charges]
    cron_jobs: ClassVar[list[Any]] = [
        # Hourly: the confirmation window is measured in hours, so this is as
        # precise as the feature needs. `run_at_startup` picks up whatever came due
        # while the worker was down (bounded by CATCH_UP_DAYS).
        cron(run_subscription_charges, minute=0, run_at_startup=True),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings_from_url(get_settings().redis_url)
