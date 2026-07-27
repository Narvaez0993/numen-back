from dataclasses import dataclass
from functools import lru_cache

from src.modules.accounts.adapters.outbound.persistence.repositories.mongo_account_repository import (  # noqa: E501
    MongoAccountRepository,
)
from src.modules.accounts.adapters.outbound.persistence.repositories.mongo_credit_card_repository import (  # noqa: E501
    MongoCreditCardRepository,
)
from src.modules.accounts.application.ports.account_repository import AccountRepository
from src.modules.accounts.application.ports.credit_card_repository import (
    CreditCardRepository,
)
from src.modules.accounts.application.use_cases.create_account import CreateAccountUseCase
from src.modules.accounts.application.use_cases.create_credit_card import (
    CreateCreditCardUseCase,
)
from src.modules.accounts.application.use_cases.delete_account import DeleteAccountUseCase
from src.modules.accounts.application.use_cases.delete_credit_card import (
    DeleteCreditCardUseCase,
)
from src.modules.accounts.application.use_cases.get_accounts_overview import (
    GetAccountsOverviewUseCase,
)
from src.modules.accounts.application.use_cases.update_account import UpdateAccountUseCase
from src.modules.accounts.application.use_cases.update_credit_card import (
    UpdateCreditCardUseCase,
)
from src.modules.auth.adapters.outbound.crypto.argon2_hasher import Argon2Hasher
from src.modules.auth.adapters.outbound.crypto.jwt_token_service import JwtTokenService
from src.modules.auth.adapters.outbound.crypto.secrets_code_generator import (
    SecretsCodeGenerator,
)
from src.modules.auth.adapters.outbound.crypto.secrets_refresh_token_issuer import (
    SecretsRefreshTokenIssuer,
)
from src.modules.auth.adapters.outbound.currency.sources_currency_scope import (
    SourcesCurrencyScope,
)
from src.modules.auth.adapters.outbound.email.logging_email_sender import LoggingEmailSender
from src.modules.auth.adapters.outbound.persistence.repositories.mongo_auth_repository import (
    MongoAuthRepository,
)
from src.modules.auth.adapters.outbound.persistence.repositories.mongo_refresh_token_repository import (  # noqa: E501
    MongoRefreshTokenRepository,
)
from src.modules.auth.adapters.outbound.persistence.repositories.mongo_verification_code_repository import (  # noqa: E501
    MongoVerificationCodeRepository,
)
from src.modules.auth.application.ports.auth_repository import AuthRepository
from src.modules.auth.application.ports.code_generator import CodeGenerator
from src.modules.auth.application.ports.currency_scope import CurrencyScope
from src.modules.auth.application.ports.email_sender import EmailSender
from src.modules.auth.application.ports.password_hasher import PasswordHasher
from src.modules.auth.application.ports.refresh_token_issuer import RefreshTokenIssuer
from src.modules.auth.application.ports.refresh_token_repository import RefreshTokenRepository
from src.modules.auth.application.ports.token_service import TokenService
from src.modules.auth.application.ports.verification_code_repository import (
    VerificationCodeRepository,
)
from src.modules.auth.application.services.session_issuer import SessionIssuer
from src.modules.auth.application.use_cases.login import LoginUseCase
from src.modules.auth.application.use_cases.logout import LogoutUseCase
from src.modules.auth.application.use_cases.refresh import RefreshUseCase
from src.modules.auth.application.use_cases.register import RegisterUseCase
from src.modules.auth.application.use_cases.resend_code import ResendCodeUseCase
from src.modules.auth.application.use_cases.update_display_name import (
    UpdateDisplayNameUseCase,
)
from src.modules.auth.application.use_cases.update_preferences import (
    UpdatePreferencesUseCase,
)
from src.modules.auth.application.use_cases.verify_email import VerifyEmailUseCase
from src.modules.budgets.adapters.outbound.catalog.categories_category_reader import (
    CategoriesCategoryReader as BudgetsCategoryReaderAdapter,
)
from src.modules.budgets.adapters.outbound.persistence.repositories.mongo_budget_repository import (
    MongoBudgetRepository,
)
from src.modules.budgets.adapters.outbound.spend.movements_spend_reader import (
    MovementsSpendReader,
)
from src.modules.budgets.application.ports.budget_repository import BudgetRepository
from src.modules.budgets.application.ports.category_reader import (
    CategoryReader as BudgetCategoryReader,
)
from src.modules.budgets.application.ports.spend_reader import SpendReader
from src.modules.budgets.application.use_cases.create_budget import CreateBudgetUseCase
from src.modules.budgets.application.use_cases.delete_budget import DeleteBudgetUseCase
from src.modules.budgets.application.use_cases.get_budgets_snapshot import (
    GetBudgetsSnapshotUseCase,
)
from src.modules.budgets.application.use_cases.get_global_cap import GetGlobalCapUseCase
from src.modules.budgets.application.use_cases.update_budget import UpdateBudgetUseCase
from src.modules.categories.adapters.outbound.persistence.repositories.mongo_category_repository import (  # noqa: E501
    MongoCategoryRepository,
)
from src.modules.categories.application.ports.category_repository import CategoryRepository
from src.modules.categories.application.use_cases.create_category import CreateCategoryUseCase
from src.modules.categories.application.use_cases.delete_category import DeleteCategoryUseCase
from src.modules.categories.application.use_cases.list_categories import ListCategoriesUseCase
from src.modules.categories.application.use_cases.update_category import UpdateCategoryUseCase
from src.modules.movements.adapters.outbound.catalog.categories_category_lookup import (
    CategoriesCategoryLookup,
)
from src.modules.movements.adapters.outbound.ledger.accounts_source_ledger import (
    AccountsSourceLedger,
)
from src.modules.movements.adapters.outbound.persistence.repositories.mongo_idempotency_store import (  # noqa: E501
    MongoIdempotencyStore,
)
from src.modules.movements.adapters.outbound.persistence.repositories.mongo_movement_repository import (  # noqa: E501
    MongoMovementRepository,
)
from src.modules.movements.application.ports.category_lookup import CategoryLookup
from src.modules.movements.application.ports.idempotency_store import IdempotencyStore
from src.modules.movements.application.ports.movement_repository import MovementRepository
from src.modules.movements.application.ports.source_ledger import SourceLedger
from src.modules.movements.application.services.movement_references import (
    MovementReferences,
)
from src.modules.movements.application.use_cases.create_movement import CreateMovementUseCase
from src.modules.movements.application.use_cases.delete_movement import DeleteMovementUseCase
from src.modules.movements.application.use_cases.get_top_merchants import (
    GetTopMerchantsUseCase,
)
from src.modules.movements.application.use_cases.list_movements import ListMovementsUseCase
from src.modules.movements.application.use_cases.summarize_movements import (
    SummarizeMovementsUseCase,
)
from src.modules.movements.application.use_cases.update_movement import UpdateMovementUseCase
from src.modules.overview.adapters.outbound.balance.accounts_balance_reader import (
    AccountsBalanceReader,
)
from src.modules.overview.adapters.outbound.budgets.budgets_global_cap_reader import (
    BudgetsGlobalCapReader,
)
from src.modules.overview.adapters.outbound.movements.movements_summary_reader import (
    MovementsSummaryReader,
)
from src.modules.overview.adapters.outbound.subscriptions.subscriptions_upcoming_charges_reader import (  # noqa: E501
    SubscriptionsUpcomingChargesReader,
)
from src.modules.overview.application.ports.balance_reader import BalanceReader
from src.modules.overview.application.ports.budget_reader import BudgetReader
from src.modules.overview.application.ports.movement_summary_reader import (
    MovementSummaryReader,
)
from src.modules.overview.application.ports.upcoming_charges_reader import (
    UpcomingChargesReader,
)
from src.modules.overview.application.use_cases.get_home_overview import (
    GetHomeOverviewUseCase,
)
from src.modules.subscriptions.adapters.outbound.catalog.categories_category_reader import (
    CategoriesCategoryReader,
)
from src.modules.subscriptions.adapters.outbound.ledger.accounts_source_reader import (
    AccountsSourceReader,
)
from src.modules.subscriptions.adapters.outbound.ledger.movements_expense_recorder import (
    MovementsExpenseRecorder,
)
from src.modules.subscriptions.adapters.outbound.persistence.repositories.mongo_charge_repository import (  # noqa: E501
    MongoChargeRepository,
)
from src.modules.subscriptions.adapters.outbound.persistence.repositories.mongo_subscription_repository import (  # noqa: E501
    MongoSubscriptionRepository,
)
from src.modules.subscriptions.application.ports.category_reader import CategoryReader
from src.modules.subscriptions.application.ports.charge_repository import ChargeRepository
from src.modules.subscriptions.application.ports.expense_recorder import ExpenseRecorder
from src.modules.subscriptions.application.ports.source_reader import SourceReader
from src.modules.subscriptions.application.ports.subscription_repository import (
    SubscriptionRepository,
)
from src.modules.subscriptions.application.services.charge_settlement import ChargeSettlement
from src.modules.subscriptions.application.services.subscription_references import (
    SubscriptionReferences,
)
from src.modules.subscriptions.application.use_cases.confirm_charge import (
    ConfirmChargeUseCase,
)
from src.modules.subscriptions.application.use_cases.create_subscription import (
    CreateSubscriptionUseCase,
)
from src.modules.subscriptions.application.use_cases.delete_subscription import (
    DeleteSubscriptionUseCase,
)
from src.modules.subscriptions.application.use_cases.list_charges import ListChargesUseCase
from src.modules.subscriptions.application.use_cases.list_subscriptions import (
    ListSubscriptionsUseCase,
)
from src.modules.subscriptions.application.use_cases.list_upcoming_charges import (
    ListUpcomingChargesUseCase,
)
from src.modules.subscriptions.application.use_cases.open_due_charges import (
    OpenDueChargesUseCase,
)
from src.modules.subscriptions.application.use_cases.settle_unconfirmed_charges import (
    SettleUnconfirmedChargesUseCase,
)
from src.modules.subscriptions.application.use_cases.skip_charge import SkipChargeUseCase
from src.modules.subscriptions.application.use_cases.update_subscription import (
    UpdateSubscriptionUseCase,
)
from src.shared.adapters.outbound.config.settings import Settings, get_settings
from src.shared.adapters.outbound.persistence.mongo import get_mongo_client
from src.shared.adapters.outbound.persistence.mongo_unit_of_work import MongoUnitOfWork
from src.shared.adapters.outbound.time.system_clock import SystemClock
from src.shared.application.ports.clock import Clock
from src.shared.application.ports.unit_of_work import UnitOfWork


@dataclass
class Container:
    """Composition root: instantiates ports' implementations and use cases.

    Routers (adapters/inbound/http) pull from here via FastAPI Depends. Workers
    pull from here on startup. Tests can replace specific fields with fakes.
    """

    settings: Settings

    # Ports → outbound adapters
    auth_repository: AuthRepository
    password_hasher: PasswordHasher
    token_service: TokenService
    clock: Clock
    unit_of_work: UnitOfWork
    verification_code_repository: VerificationCodeRepository
    refresh_token_repository: RefreshTokenRepository
    code_generator: CodeGenerator
    refresh_token_issuer: RefreshTokenIssuer
    email_sender: EmailSender
    currency_scope: CurrencyScope

    # Use cases (inbound ports)
    login_use_case: LoginUseCase
    register_use_case: RegisterUseCase
    verify_email_use_case: VerifyEmailUseCase
    resend_code_use_case: ResendCodeUseCase
    refresh_use_case: RefreshUseCase
    logout_use_case: LogoutUseCase
    update_display_name_use_case: UpdateDisplayNameUseCase
    update_preferences_use_case: UpdatePreferencesUseCase

    # Categories
    category_repository: CategoryRepository
    list_categories_use_case: ListCategoriesUseCase
    create_category_use_case: CreateCategoryUseCase
    update_category_use_case: UpdateCategoryUseCase
    delete_category_use_case: DeleteCategoryUseCase

    # Accounts + credit cards
    account_repository: AccountRepository
    credit_card_repository: CreditCardRepository
    get_accounts_overview_use_case: GetAccountsOverviewUseCase
    create_account_use_case: CreateAccountUseCase
    update_account_use_case: UpdateAccountUseCase
    delete_account_use_case: DeleteAccountUseCase
    create_credit_card_use_case: CreateCreditCardUseCase
    update_credit_card_use_case: UpdateCreditCardUseCase
    delete_credit_card_use_case: DeleteCreditCardUseCase

    # Movements
    movement_repository: MovementRepository
    source_ledger: SourceLedger
    category_lookup: CategoryLookup
    idempotency_store: IdempotencyStore
    movement_references: MovementReferences
    create_movement_use_case: CreateMovementUseCase
    list_movements_use_case: ListMovementsUseCase
    update_movement_use_case: UpdateMovementUseCase
    delete_movement_use_case: DeleteMovementUseCase
    summarize_movements_use_case: SummarizeMovementsUseCase
    get_top_merchants_use_case: GetTopMerchantsUseCase

    # Budgets
    budget_repository: BudgetRepository
    budget_spend_reader: SpendReader
    budget_category_reader: BudgetCategoryReader
    get_budgets_snapshot_use_case: GetBudgetsSnapshotUseCase
    get_global_cap_use_case: GetGlobalCapUseCase
    create_budget_use_case: CreateBudgetUseCase
    update_budget_use_case: UpdateBudgetUseCase
    delete_budget_use_case: DeleteBudgetUseCase

    # Subscriptions
    subscription_repository: SubscriptionRepository
    subscription_source_reader: SourceReader
    subscription_category_reader: CategoryReader
    subscription_references: SubscriptionReferences
    list_subscriptions_use_case: ListSubscriptionsUseCase
    create_subscription_use_case: CreateSubscriptionUseCase
    update_subscription_use_case: UpdateSubscriptionUseCase
    delete_subscription_use_case: DeleteSubscriptionUseCase
    charge_repository: ChargeRepository
    expense_recorder: ExpenseRecorder
    charge_settlement: ChargeSettlement
    list_charges_use_case: ListChargesUseCase
    confirm_charge_use_case: ConfirmChargeUseCase
    skip_charge_use_case: SkipChargeUseCase
    open_due_charges_use_case: OpenDueChargesUseCase
    settle_unconfirmed_charges_use_case: SettleUnconfirmedChargesUseCase

    # Overview (Home) — the only module that reads across the others
    list_upcoming_charges_use_case: ListUpcomingChargesUseCase
    balance_reader: BalanceReader
    movement_summary_reader: MovementSummaryReader
    upcoming_charges_reader: UpcomingChargesReader
    budget_cap_reader: BudgetReader
    get_home_overview_use_case: GetHomeOverviewUseCase


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()

    auth_repository: AuthRepository = MongoAuthRepository()
    password_hasher: PasswordHasher = Argon2Hasher()
    token_service: TokenService = JwtTokenService(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        access_ttl_minutes=settings.jwt_access_ttl_minutes,
    )
    clock: Clock = SystemClock()
    unit_of_work: UnitOfWork = MongoUnitOfWork(get_mongo_client(settings))
    verification_code_repository: VerificationCodeRepository = MongoVerificationCodeRepository()
    refresh_token_repository: RefreshTokenRepository = MongoRefreshTokenRepository()
    code_generator: CodeGenerator = SecretsCodeGenerator(length=settings.verification_code_length)
    refresh_token_issuer: RefreshTokenIssuer = SecretsRefreshTokenIssuer()
    email_sender: EmailSender = LoggingEmailSender()
    currency_scope: CurrencyScope = SourcesCurrencyScope()
    category_repository: CategoryRepository = MongoCategoryRepository()
    account_repository: AccountRepository = MongoAccountRepository()
    credit_card_repository: CreditCardRepository = MongoCreditCardRepository()
    movement_repository: MovementRepository = MongoMovementRepository()
    idempotency_store: IdempotencyStore = MongoIdempotencyStore()
    source_ledger: SourceLedger = AccountsSourceLedger(
        account_repository=account_repository,
        credit_card_repository=credit_card_repository,
    )
    category_lookup: CategoryLookup = CategoriesCategoryLookup(
        category_repository=category_repository,
    )
    movement_references = MovementReferences(
        source_ledger=source_ledger,
        category_lookup=category_lookup,
    )

    accounts_overview_use_case = GetAccountsOverviewUseCase(
        account_repository=account_repository,
        credit_card_repository=credit_card_repository,
    )
    summarize_movements_use_case = SummarizeMovementsUseCase(
        movement_repository=movement_repository,
    )
    list_movements_use_case = ListMovementsUseCase(
        movement_repository=movement_repository,
    )
    get_top_merchants_use_case = GetTopMerchantsUseCase(
        movement_repository=movement_repository,
    )
    balance_reader: BalanceReader = AccountsBalanceReader(
        accounts_overview=accounts_overview_use_case,
    )
    movement_summary_reader: MovementSummaryReader = MovementsSummaryReader(
        summarize_movements=summarize_movements_use_case,
        list_movements=list_movements_use_case,
    )

    budget_repository: BudgetRepository = MongoBudgetRepository()
    budget_spend_reader: SpendReader = MovementsSpendReader(
        summarize_movements=summarize_movements_use_case,
        get_top_merchants=get_top_merchants_use_case,
    )
    budget_category_reader: BudgetCategoryReader = BudgetsCategoryReaderAdapter(
        category_repository=category_repository,
    )
    get_global_cap_use_case = GetGlobalCapUseCase(
        budget_repository=budget_repository,
        spend_reader=budget_spend_reader,
    )

    subscription_repository: SubscriptionRepository = MongoSubscriptionRepository()
    subscription_source_reader: SourceReader = AccountsSourceReader(
        account_repository=account_repository,
        credit_card_repository=credit_card_repository,
    )
    subscription_category_reader: CategoryReader = CategoriesCategoryReader(
        category_repository=category_repository,
    )
    subscription_references = SubscriptionReferences(
        source_reader=subscription_source_reader,
        category_reader=subscription_category_reader,
    )

    charge_repository: ChargeRepository = MongoChargeRepository()
    # The charge engine records through the movements use case, never its collection:
    # cash-basis, atomicity and idempotency stay owned by the module that defines them.
    create_movement_use_case = CreateMovementUseCase(
        movement_repository=movement_repository,
        source_ledger=source_ledger,
        references=movement_references,
        idempotency_store=idempotency_store,
        unit_of_work=unit_of_work,
        clock=clock,
    )
    expense_recorder: ExpenseRecorder = MovementsExpenseRecorder(
        create_movement=create_movement_use_case,
    )
    charge_settlement = ChargeSettlement(
        charge_repository=charge_repository,
        subscription_repository=subscription_repository,
        expense_recorder=expense_recorder,
        unit_of_work=unit_of_work,
        clock=clock,
    )

    list_upcoming_charges_use_case = ListUpcomingChargesUseCase(
        subscription_repository=subscription_repository,
        charge_repository=charge_repository,
    )
    upcoming_charges_reader: UpcomingChargesReader = SubscriptionsUpcomingChargesReader(
        list_upcoming=list_upcoming_charges_use_case,
    )
    budget_cap_reader: BudgetReader = BudgetsGlobalCapReader(
        get_global_cap=get_global_cap_use_case,
    )

    session_issuer = SessionIssuer(
        token_service=token_service,
        refresh_token_issuer=refresh_token_issuer,
        refresh_token_repository=refresh_token_repository,
        clock=clock,
        refresh_ttl_days=settings.jwt_refresh_ttl_days,
    )

    return Container(
        settings=settings,
        auth_repository=auth_repository,
        password_hasher=password_hasher,
        token_service=token_service,
        clock=clock,
        unit_of_work=unit_of_work,
        verification_code_repository=verification_code_repository,
        refresh_token_repository=refresh_token_repository,
        code_generator=code_generator,
        refresh_token_issuer=refresh_token_issuer,
        email_sender=email_sender,
        currency_scope=currency_scope,
        login_use_case=LoginUseCase(
            auth_repository=auth_repository,
            password_hasher=password_hasher,
            session_issuer=session_issuer,
        ),
        register_use_case=RegisterUseCase(
            auth_repository=auth_repository,
            password_hasher=password_hasher,
            code_generator=code_generator,
            verification_code_repository=verification_code_repository,
            email_sender=email_sender,
            clock=clock,
            code_ttl_minutes=settings.verification_code_ttl_minutes,
            resend_cooldown_seconds=settings.verification_resend_cooldown_seconds,
        ),
        verify_email_use_case=VerifyEmailUseCase(
            auth_repository=auth_repository,
            verification_code_repository=verification_code_repository,
            session_issuer=session_issuer,
            clock=clock,
            max_attempts=settings.verification_max_attempts,
        ),
        resend_code_use_case=ResendCodeUseCase(
            auth_repository=auth_repository,
            verification_code_repository=verification_code_repository,
            code_generator=code_generator,
            email_sender=email_sender,
            clock=clock,
            code_ttl_minutes=settings.verification_code_ttl_minutes,
            resend_cooldown_seconds=settings.verification_resend_cooldown_seconds,
        ),
        refresh_use_case=RefreshUseCase(
            auth_repository=auth_repository,
            refresh_token_repository=refresh_token_repository,
            refresh_token_issuer=refresh_token_issuer,
            session_issuer=session_issuer,
            clock=clock,
        ),
        logout_use_case=LogoutUseCase(
            refresh_token_repository=refresh_token_repository,
            refresh_token_issuer=refresh_token_issuer,
            clock=clock,
        ),
        update_display_name_use_case=UpdateDisplayNameUseCase(
            auth_repository=auth_repository,
        ),
        update_preferences_use_case=UpdatePreferencesUseCase(
            auth_repository=auth_repository,
            currency_scope=currency_scope,
            unit_of_work=unit_of_work,
        ),
        category_repository=category_repository,
        list_categories_use_case=ListCategoriesUseCase(
            category_repository=category_repository,
        ),
        create_category_use_case=CreateCategoryUseCase(
            category_repository=category_repository,
            free_limit=settings.categories_free_limit,
        ),
        update_category_use_case=UpdateCategoryUseCase(
            category_repository=category_repository,
        ),
        delete_category_use_case=DeleteCategoryUseCase(
            category_repository=category_repository,
        ),
        account_repository=account_repository,
        credit_card_repository=credit_card_repository,
        get_accounts_overview_use_case=accounts_overview_use_case,
        create_account_use_case=CreateAccountUseCase(
            account_repository=account_repository,
            clock=clock,
            free_limit=settings.accounts_free_limit,
        ),
        update_account_use_case=UpdateAccountUseCase(
            account_repository=account_repository,
        ),
        delete_account_use_case=DeleteAccountUseCase(
            account_repository=account_repository,
        ),
        create_credit_card_use_case=CreateCreditCardUseCase(
            credit_card_repository=credit_card_repository,
            clock=clock,
            free_limit=settings.credit_cards_free_limit,
        ),
        update_credit_card_use_case=UpdateCreditCardUseCase(
            credit_card_repository=credit_card_repository,
        ),
        delete_credit_card_use_case=DeleteCreditCardUseCase(
            credit_card_repository=credit_card_repository,
        ),
        movement_repository=movement_repository,
        source_ledger=source_ledger,
        category_lookup=category_lookup,
        idempotency_store=idempotency_store,
        movement_references=movement_references,
        create_movement_use_case=create_movement_use_case,
        list_movements_use_case=list_movements_use_case,
        update_movement_use_case=UpdateMovementUseCase(
            movement_repository=movement_repository,
            source_ledger=source_ledger,
            references=movement_references,
            unit_of_work=unit_of_work,
            clock=clock,
        ),
        delete_movement_use_case=DeleteMovementUseCase(
            movement_repository=movement_repository,
            source_ledger=source_ledger,
            unit_of_work=unit_of_work,
        ),
        summarize_movements_use_case=summarize_movements_use_case,
        get_top_merchants_use_case=get_top_merchants_use_case,
        budget_repository=budget_repository,
        budget_spend_reader=budget_spend_reader,
        budget_category_reader=budget_category_reader,
        get_budgets_snapshot_use_case=GetBudgetsSnapshotUseCase(
            budget_repository=budget_repository,
            spend_reader=budget_spend_reader,
        ),
        get_global_cap_use_case=get_global_cap_use_case,
        create_budget_use_case=CreateBudgetUseCase(
            budget_repository=budget_repository,
            category_reader=budget_category_reader,
            category_free_limit=settings.budget_categories_free_limit,
        ),
        update_budget_use_case=UpdateBudgetUseCase(budget_repository=budget_repository),
        delete_budget_use_case=DeleteBudgetUseCase(budget_repository=budget_repository),
        subscription_repository=subscription_repository,
        subscription_source_reader=subscription_source_reader,
        subscription_category_reader=subscription_category_reader,
        subscription_references=subscription_references,
        list_subscriptions_use_case=ListSubscriptionsUseCase(
            subscription_repository=subscription_repository,
        ),
        create_subscription_use_case=CreateSubscriptionUseCase(
            subscription_repository=subscription_repository,
            references=subscription_references,
            clock=clock,
        ),
        update_subscription_use_case=UpdateSubscriptionUseCase(
            subscription_repository=subscription_repository,
            references=subscription_references,
        ),
        delete_subscription_use_case=DeleteSubscriptionUseCase(
            subscription_repository=subscription_repository,
        ),
        charge_repository=charge_repository,
        expense_recorder=expense_recorder,
        charge_settlement=charge_settlement,
        list_charges_use_case=ListChargesUseCase(charge_repository=charge_repository),
        confirm_charge_use_case=ConfirmChargeUseCase(
            charge_repository=charge_repository,
            settlement=charge_settlement,
        ),
        skip_charge_use_case=SkipChargeUseCase(
            charge_repository=charge_repository,
            settlement=charge_settlement,
        ),
        open_due_charges_use_case=OpenDueChargesUseCase(
            subscription_repository=subscription_repository,
            charge_repository=charge_repository,
            clock=clock,
        ),
        settle_unconfirmed_charges_use_case=SettleUnconfirmedChargesUseCase(
            charge_repository=charge_repository,
            settlement=charge_settlement,
            clock=clock,
        ),
        list_upcoming_charges_use_case=list_upcoming_charges_use_case,
        balance_reader=balance_reader,
        movement_summary_reader=movement_summary_reader,
        upcoming_charges_reader=upcoming_charges_reader,
        budget_cap_reader=budget_cap_reader,
        get_home_overview_use_case=GetHomeOverviewUseCase(
            balance_reader=balance_reader,
            movement_summary_reader=movement_summary_reader,
            upcoming_charges_reader=upcoming_charges_reader,
            budget_reader=budget_cap_reader,
        ),
    )


@lru_cache
def get_container() -> Container:
    return build_container()


def reset_container() -> None:
    """For tests: clear the cached container so the next call rebuilds it.

    To inject test doubles, build a fresh container and set it via FastAPI's
    `app.dependency_overrides[get_container] = lambda: my_container`.
    """
    get_container.cache_clear()
