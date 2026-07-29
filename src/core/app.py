from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.di.container import get_container
from src.modules.accounts.adapters.inbound.http.routers import (
    credit_cards_router,
)
from src.modules.accounts.adapters.inbound.http.routers import (
    router as accounts_router,
)
from src.modules.accounts.adapters.outbound.persistence.documents.account_document import (
    AccountDocument,
)
from src.modules.accounts.adapters.outbound.persistence.documents.credit_card_document import (
    CreditCardDocument,
)
from src.modules.assistant.adapters.inbound.http.routers import (
    router as assistant_router,
)
from src.modules.assistant.adapters.outbound.persistence.documents.action_log_document import (
    AIActionLogDocument,
)
from src.modules.assistant.adapters.outbound.persistence.documents.chat_message_document import (
    ChatMessageDocument,
)
from src.modules.assistant.adapters.outbound.persistence.documents.movement_draft_document import (
    MovementDraftDocument,
)
from src.modules.assistant.adapters.outbound.persistence.documents.usage_counter_document import (
    AIUsageCounterDocument,
)
from src.modules.auth.adapters.inbound.http.routers import router as auth_router
from src.modules.auth.adapters.outbound.persistence.documents.email_verification_code_document import (  # noqa: E501
    EmailVerificationCodeDocument,
)
from src.modules.auth.adapters.outbound.persistence.documents.refresh_token_document import (
    RefreshTokenDocument,
)
from src.modules.auth.adapters.outbound.persistence.documents.user_document import UserDocument
from src.modules.budgets.adapters.inbound.http.routers import (
    router as budgets_router,
)
from src.modules.budgets.adapters.outbound.persistence.documents.budget_document import (
    BudgetDocument,
)
from src.modules.categories.adapters.inbound.http.routers import (
    router as categories_router,
)
from src.modules.categories.adapters.outbound.persistence.documents.category_document import (
    CategoryDocument,
)
from src.modules.debts.adapters.inbound.http.routers import (
    router as debts_router,
)
from src.modules.debts.adapters.outbound.persistence.documents.counterparty_document import (
    CounterpartyDocument,
)
from src.modules.debts.adapters.outbound.persistence.documents.debt_document import (
    DebtDocument,
)
from src.modules.debts.adapters.outbound.persistence.documents.shared_event_document import (
    SharedEventDocument,
)
from src.modules.goals.adapters.inbound.http.routers import (
    router as goals_router,
)
from src.modules.goals.adapters.outbound.persistence.documents.goal_document import (
    GoalDocument,
)
from src.modules.movements.adapters.inbound.http.routers import (
    router as movements_router,
)
from src.modules.movements.adapters.outbound.persistence.documents.idempotency_key_document import (
    IdempotencyKeyDocument,
)
from src.modules.movements.adapters.outbound.persistence.documents.movement_document import (
    MovementDocument,
)
from src.modules.overview.adapters.inbound.http.routers import (
    router as home_router,
)
from src.modules.subscriptions.adapters.inbound.http.charge_routers import (
    router as subscription_charges_router,
)
from src.modules.subscriptions.adapters.inbound.http.routers import (
    router as subscriptions_router,
)
from src.modules.subscriptions.adapters.outbound.persistence.documents.subscription_charge_document import (  # noqa: E501
    SubscriptionChargeDocument,
)
from src.modules.subscriptions.adapters.outbound.persistence.documents.subscription_document import (  # noqa: E501
    SubscriptionDocument,
)
from src.shared.adapters.inbound.http.exception_handlers import register_exception_handlers
from src.shared.adapters.outbound.config.settings import get_settings
from src.shared.adapters.outbound.logging.setup import configure_logging
from src.shared.adapters.outbound.persistence.mongo import close_mongo_client, init_persistence

# All Beanie documents must be listed here so they are registered on startup.
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
    BudgetDocument,
    DebtDocument,
    CounterpartyDocument,
    SharedEventDocument,
    GoalDocument,
    ChatMessageDocument,
    MovementDraftDocument,
    AIUsageCounterDocument,
    AIActionLogDocument,
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    await init_persistence(settings, _DOCUMENTS)
    # Warm the container cache so DI is ready
    get_container()
    yield
    await close_mongo_client()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="back-deshka",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(auth_router)
    app.include_router(categories_router)
    app.include_router(accounts_router)
    app.include_router(credit_cards_router)
    app.include_router(movements_router)
    app.include_router(subscriptions_router)
    app.include_router(subscription_charges_router)
    app.include_router(budgets_router)
    app.include_router(debts_router)
    app.include_router(goals_router)
    app.include_router(assistant_router)
    app.include_router(home_router)

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["meta"])
    async def readyz() -> dict[str, str]:
        # TODO: ping Mongo + Redis here when adding production hardening
        return {"status": "ok"}

    return app


app = create_app()
