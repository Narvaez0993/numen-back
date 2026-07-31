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
from src.modules.assistant.adapters.outbound.accounts.accounts_accounts_reader import (
    AccountsAccountsReader,
)
from src.modules.assistant.adapters.outbound.ai.anthropic_agent_model import AnthropicAgentModel
from src.modules.assistant.adapters.outbound.auth.auth_users_reader import AuthUsersReader
from src.modules.assistant.adapters.outbound.budgets.budgets_budget_writer import (
    BudgetsBudgetWriter,
)
from src.modules.assistant.adapters.outbound.budgets.budgets_budgets_reader import (
    BudgetsBudgetsReader,
)
from src.modules.assistant.adapters.outbound.categories.categories_categories_reader import (
    CategoriesCategoriesReader,
)
from src.modules.assistant.adapters.outbound.debts.debts_debts_reader import DebtsDebtsReader
from src.modules.assistant.adapters.outbound.goals.goals_goal_contributor import (
    GoalsGoalContributor,
)
from src.modules.assistant.adapters.outbound.goals.goals_goals_reader import GoalsGoalsReader
from src.modules.assistant.adapters.outbound.ledger.movements_movement_recorder import (
    MovementsMovementRecorder,
)
from src.modules.assistant.adapters.outbound.movements.movements_movements_reader import (
    MovementsMovementsReader,
)
from src.modules.assistant.adapters.outbound.persistence.repositories.mongo_action_log import (
    MongoAIActionLog,
)
from src.modules.assistant.adapters.outbound.persistence.repositories.mongo_agent_outputs import (
    MongoAgentOutputs,
)
from src.modules.assistant.adapters.outbound.persistence.repositories.mongo_chat_messages import (
    MongoChatMessageRepository,
)
from src.modules.assistant.adapters.outbound.persistence.repositories.mongo_dismissals import (
    MongoInsightDismissals,
)
from src.modules.assistant.adapters.outbound.persistence.repositories.mongo_drafts import (
    MongoMovementDraftRepository,
)
from src.modules.assistant.adapters.outbound.persistence.repositories.mongo_usage_counters import (
    MongoAIUsageCounters,
)
from src.modules.assistant.adapters.outbound.subscriptions.subscriptions_reader import (
    SubscriptionsSubscriptionsReader,
)
from src.modules.assistant.application.ports.accounts_reader import (
    AccountsReader as AssistantAccountsReader,
)
from src.modules.assistant.application.ports.action_log import ActionLog
from src.modules.assistant.application.ports.agent_model import AgentModel
from src.modules.assistant.application.ports.agent_output_repository import (
    AgentOutputRepository,
)
from src.modules.assistant.application.ports.budget_writer import BudgetWriter
from src.modules.assistant.application.ports.budgets_reader import (
    BudgetsReader as AssistantBudgetsReader,
)
from src.modules.assistant.application.ports.categories_reader import (
    CategoriesReader as AssistantCategoriesReader,
)
from src.modules.assistant.application.ports.chat_message_repository import ChatMessageRepository
from src.modules.assistant.application.ports.debts_reader import (
    DebtsReader as AssistantDebtsReader,
)
from src.modules.assistant.application.ports.draft_repository import DraftRepository
from src.modules.assistant.application.ports.goal_contributor import GoalContributor
from src.modules.assistant.application.ports.goals_reader import (
    GoalsReader as AssistantGoalsReader,
)
from src.modules.assistant.application.ports.insight_dismissals import InsightDismissals
from src.modules.assistant.application.ports.movement_recorder import (
    MovementRecorder as AssistantMovementRecorder,
)
from src.modules.assistant.application.ports.movements_reader import (
    MovementsReader as AssistantMovementsReader,
)
from src.modules.assistant.application.ports.subscriptions_reader import (
    SubscriptionsReader as AssistantSubscriptionsReader,
)
from src.modules.assistant.application.ports.usage_counters import UsageCounters
from src.modules.assistant.application.ports.users_reader import UsersReader
from src.modules.assistant.application.pricing import ModelPricing, PlanLimits
from src.modules.assistant.application.services.tool_registry import ToolRegistry
from src.modules.assistant.application.use_cases.apply_play import ApplyPlayUseCase
from src.modules.assistant.application.use_cases.compose_monthly_summary import (
    ComposeMonthlySummaryUseCase,
)
from src.modules.assistant.application.use_cases.compose_weekly_review import (
    ComposeWeeklyReviewUseCase,
)
from src.modules.assistant.application.use_cases.confirm_draft import ConfirmDraftUseCase
from src.modules.assistant.application.use_cases.discard_draft import DiscardDraftUseCase
from src.modules.assistant.application.use_cases.dismiss_insight import DismissInsightUseCase
from src.modules.assistant.application.use_cases.dismiss_output import DismissOutputUseCase
from src.modules.assistant.application.use_cases.get_chat_history import GetChatHistoryUseCase
from src.modules.assistant.application.use_cases.get_feed import GetAssistantFeedUseCase
from src.modules.assistant.application.use_cases.get_output import GetOutputUseCase
from src.modules.assistant.application.use_cases.get_usage import GetUsageUseCase
from src.modules.assistant.application.use_cases.list_outputs import ListOutputsUseCase
from src.modules.assistant.application.use_cases.mark_output_read import MarkOutputReadUseCase
from src.modules.assistant.application.use_cases.parse_capture import ParseCaptureUseCase
from src.modules.assistant.application.use_cases.run_monthly_summaries import (
    RunMonthlySummariesUseCase,
)
from src.modules.assistant.application.use_cases.run_weekly_reviews import (
    RunWeeklyReviewsUseCase,
)
from src.modules.assistant.application.use_cases.send_chat_message import SendChatMessageUseCase
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
from src.modules.debts.adapters.outbound.persistence.repositories.mongo_counterparty_repository import (  # noqa: E501
    MongoCounterpartyRepository,
)
from src.modules.debts.adapters.outbound.persistence.repositories.mongo_debt_repository import (
    MongoDebtRepository,
)
from src.modules.debts.adapters.outbound.persistence.repositories.mongo_shared_event_repository import (  # noqa: E501
    MongoSharedEventRepository,
)
from src.modules.debts.application.ports.counterparty_repository import (
    CounterpartyRepository,
)
from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.debts.application.ports.event_repository import EventRepository
from src.modules.debts.application.services.counterparty_resolver import (
    CounterpartyResolver,
)
from src.modules.debts.application.use_cases.add_payment import AddPaymentUseCase
from src.modules.debts.application.use_cases.create_debt import CreateDebtUseCase
from src.modules.debts.application.use_cases.create_shared_event import (
    CreateSharedEventUseCase,
)
from src.modules.debts.application.use_cases.delete_debt import DeleteDebtUseCase
from src.modules.debts.application.use_cases.get_debt_totals import GetDebtTotalsUseCase
from src.modules.debts.application.use_cases.get_debts_snapshot import (
    GetDebtsSnapshotUseCase,
)
from src.modules.debts.application.use_cases.remove_payment import RemovePaymentUseCase
from src.modules.debts.application.use_cases.update_debt import UpdateDebtUseCase
from src.modules.goals.adapters.outbound.funds.movements_funds_reader import (
    MovementsFundsReader,
)
from src.modules.goals.adapters.outbound.ledger.movements_transfer_recorder import (
    MovementsTransferRecorder,
)
from src.modules.goals.adapters.outbound.persistence.repositories.mongo_goal_repository import (
    MongoGoalRepository,
)
from src.modules.goals.application.ports.funds_reader import FundsReader
from src.modules.goals.application.ports.goal_repository import GoalRepository
from src.modules.goals.application.ports.transfer_recorder import TransferRecorder
from src.modules.goals.application.use_cases.contribute import ContributeUseCase
from src.modules.goals.application.use_cases.create_goal import CreateGoalUseCase
from src.modules.goals.application.use_cases.delete_goal import DeleteGoalUseCase
from src.modules.goals.application.use_cases.get_goals_snapshot import (
    GetGoalsSnapshotUseCase,
)
from src.modules.goals.application.use_cases.get_top_goal import GetTopGoalUseCase
from src.modules.goals.application.use_cases.update_goal import UpdateGoalUseCase
from src.modules.goals.application.use_cases.withdraw import WithdrawUseCase
from src.modules.movements.adapters.outbound.catalog.categories_category_lookup import (
    CategoriesCategoryLookup,
)
from src.modules.movements.adapters.outbound.ledger.accounts_source_ledger import (
    AccountsSourceLedger,
)
from src.modules.movements.adapters.outbound.ledger.goals_pocket_ledger import (
    GoalsPocketLedger,
)
from src.modules.movements.adapters.outbound.ledger.routing_source_ledger import (
    RoutingSourceLedger,
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
from src.modules.movements.application.use_cases.get_daily_spend import (
    GetDailySpendUseCase,
)
from src.modules.movements.application.use_cases.get_goal_funds import (
    GetGoalFundsUseCase,
)
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
from src.modules.overview.adapters.outbound.debts.debts_debt_reader import (
    DebtsDebtReader,
)
from src.modules.overview.adapters.outbound.goals.goals_goal_reader import (
    GoalsGoalReader,
)
from src.modules.overview.adapters.outbound.movements.movements_summary_reader import (
    MovementsSummaryReader,
)
from src.modules.overview.adapters.outbound.subscriptions.subscriptions_upcoming_charges_reader import (  # noqa: E501
    SubscriptionsUpcomingChargesReader,
)
from src.modules.overview.application.ports.balance_reader import BalanceReader
from src.modules.overview.application.ports.budget_reader import BudgetReader
from src.modules.overview.application.ports.debt_reader import DebtReader
from src.modules.overview.application.ports.goal_reader import GoalReader
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
    get_daily_spend_use_case: GetDailySpendUseCase
    get_goal_funds_use_case: GetGoalFundsUseCase

    # Budgets
    budget_repository: BudgetRepository
    budget_spend_reader: SpendReader
    budget_category_reader: BudgetCategoryReader
    get_budgets_snapshot_use_case: GetBudgetsSnapshotUseCase
    get_global_cap_use_case: GetGlobalCapUseCase
    create_budget_use_case: CreateBudgetUseCase
    update_budget_use_case: UpdateBudgetUseCase
    delete_budget_use_case: DeleteBudgetUseCase

    # Debts
    debt_repository: DebtRepository
    counterparty_repository: CounterpartyRepository
    event_repository: EventRepository
    get_debts_snapshot_use_case: GetDebtsSnapshotUseCase
    get_debt_totals_use_case: GetDebtTotalsUseCase
    create_debt_use_case: CreateDebtUseCase
    create_shared_event_use_case: CreateSharedEventUseCase
    update_debt_use_case: UpdateDebtUseCase
    delete_debt_use_case: DeleteDebtUseCase
    add_payment_use_case: AddPaymentUseCase
    remove_payment_use_case: RemovePaymentUseCase

    # Goals
    goal_repository: GoalRepository
    goal_funds_reader: FundsReader
    goal_transfer_recorder: TransferRecorder
    get_goals_snapshot_use_case: GetGoalsSnapshotUseCase
    get_top_goal_use_case: GetTopGoalUseCase
    create_goal_use_case: CreateGoalUseCase
    update_goal_use_case: UpdateGoalUseCase
    delete_goal_use_case: DeleteGoalUseCase
    contribute_use_case: ContributeUseCase
    withdraw_use_case: WithdrawUseCase

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
    debt_totals_reader: DebtReader
    top_goal_reader: GoalReader
    get_home_overview_use_case: GetHomeOverviewUseCase

    # Assistant — the agent: model port, tools over the other modules, ledgers
    chat_message_repository: ChatMessageRepository
    movement_draft_repository: DraftRepository
    assistant_usage_counters: UsageCounters
    assistant_insight_dismissals: InsightDismissals
    assistant_agent_outputs: AgentOutputRepository
    assistant_users_reader: UsersReader
    assistant_budget_writer: BudgetWriter
    assistant_goal_contributor: GoalContributor
    assistant_action_log: ActionLog
    assistant_agent_model: AgentModel
    assistant_accounts_reader: AssistantAccountsReader
    assistant_movements_reader: AssistantMovementsReader
    assistant_budgets_reader: AssistantBudgetsReader
    assistant_goals_reader: AssistantGoalsReader
    assistant_debts_reader: AssistantDebtsReader
    assistant_subscriptions_reader: AssistantSubscriptionsReader
    assistant_categories_reader: AssistantCategoriesReader
    assistant_movement_recorder: AssistantMovementRecorder
    assistant_tool_registry: ToolRegistry
    send_chat_message_use_case: SendChatMessageUseCase
    parse_capture_use_case: ParseCaptureUseCase
    get_chat_history_use_case: GetChatHistoryUseCase
    confirm_draft_use_case: ConfirmDraftUseCase
    discard_draft_use_case: DiscardDraftUseCase
    get_assistant_usage_use_case: GetUsageUseCase
    get_assistant_feed_use_case: GetAssistantFeedUseCase
    dismiss_insight_use_case: DismissInsightUseCase
    compose_monthly_summary_use_case: ComposeMonthlySummaryUseCase
    run_monthly_summaries_use_case: RunMonthlySummariesUseCase
    compose_weekly_review_use_case: ComposeWeeklyReviewUseCase
    run_weekly_reviews_use_case: RunWeeklyReviewsUseCase
    apply_play_use_case: ApplyPlayUseCase
    list_outputs_use_case: ListOutputsUseCase
    get_output_use_case: GetOutputUseCase
    mark_output_read_use_case: MarkOutputReadUseCase
    dismiss_output_use_case: DismissOutputUseCase


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
    goal_repository: GoalRepository = MongoGoalRepository()
    # One ledger over every endpoint kind: accounts and cards move for real, a pocket
    # is a no-op leg because its money is the sum of the movements themselves.
    source_ledger: SourceLedger = RoutingSourceLedger(
        accounts=AccountsSourceLedger(
            account_repository=account_repository,
            credit_card_repository=credit_card_repository,
        ),
        goals=GoalsPocketLedger(goal_repository=goal_repository),
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
    get_daily_spend_use_case = GetDailySpendUseCase(
        movement_repository=movement_repository,
    )
    get_goal_funds_use_case = GetGoalFundsUseCase(
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

    debt_repository: DebtRepository = MongoDebtRepository()
    counterparty_repository: CounterpartyRepository = MongoCounterpartyRepository()
    event_repository: EventRepository = MongoSharedEventRepository()
    counterparty_resolver = CounterpartyResolver(
        counterparty_repository=counterparty_repository,
    )
    get_debts_snapshot_use_case = GetDebtsSnapshotUseCase(
        debt_repository=debt_repository,
        counterparty_repository=counterparty_repository,
        event_repository=event_repository,
    )
    get_debt_totals_use_case = GetDebtTotalsUseCase(debt_repository=debt_repository)

    goal_funds_reader: FundsReader = MovementsFundsReader(
        get_goal_funds=get_goal_funds_use_case,
    )
    get_goals_snapshot_use_case = GetGoalsSnapshotUseCase(
        goal_repository=goal_repository,
        funds_reader=goal_funds_reader,
    )
    get_top_goal_use_case = GetTopGoalUseCase(
        goal_repository=goal_repository,
        funds_reader=goal_funds_reader,
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
    goal_transfer_recorder: TransferRecorder = MovementsTransferRecorder(
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
    debt_totals_reader: DebtReader = DebtsDebtReader(
        get_debt_totals=get_debt_totals_use_case,
    )
    top_goal_reader: GoalReader = GoalsGoalReader(
        get_top_goal=get_top_goal_use_case,
    )

    # Assistant: locals for use cases other modules declared inline until now
    list_categories_use_case = ListCategoriesUseCase(
        category_repository=category_repository,
    )
    get_budgets_snapshot_use_case = GetBudgetsSnapshotUseCase(
        budget_repository=budget_repository,
        spend_reader=budget_spend_reader,
    )
    list_subscriptions_use_case = ListSubscriptionsUseCase(
        subscription_repository=subscription_repository,
    )

    chat_message_repository: ChatMessageRepository = MongoChatMessageRepository()
    movement_draft_repository: DraftRepository = MongoMovementDraftRepository()
    assistant_usage_counters: UsageCounters = MongoAIUsageCounters()
    assistant_insight_dismissals: InsightDismissals = MongoInsightDismissals()
    assistant_agent_outputs: AgentOutputRepository = MongoAgentOutputs()
    assistant_users_reader: UsersReader = AuthUsersReader()
    assistant_action_log: ActionLog = MongoAIActionLog()
    assistant_agent_model: AgentModel = AnthropicAgentModel(
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
        max_tokens=settings.anthropic_max_tokens,
        effort=settings.anthropic_effort,
    )
    assistant_accounts_reader: AssistantAccountsReader = AccountsAccountsReader(
        get_accounts_overview=accounts_overview_use_case,
    )
    assistant_movements_reader: AssistantMovementsReader = MovementsMovementsReader(
        summarize_movements=summarize_movements_use_case,
        list_movements=list_movements_use_case,
        get_top_merchants=get_top_merchants_use_case,
        get_daily_spend=get_daily_spend_use_case,
    )
    assistant_budgets_reader: AssistantBudgetsReader = BudgetsBudgetsReader(
        get_budgets_snapshot=get_budgets_snapshot_use_case,
    )
    assistant_goals_reader: AssistantGoalsReader = GoalsGoalsReader(
        get_goals_snapshot=get_goals_snapshot_use_case,
    )
    assistant_debts_reader: AssistantDebtsReader = DebtsDebtsReader(
        get_debts_snapshot=get_debts_snapshot_use_case,
    )
    assistant_subscriptions_reader: AssistantSubscriptionsReader = SubscriptionsSubscriptionsReader(
        list_subscriptions=list_subscriptions_use_case,
        list_upcoming_charges=list_upcoming_charges_use_case,
    )
    assistant_categories_reader: AssistantCategoriesReader = CategoriesCategoriesReader(
        list_categories=list_categories_use_case,
    )
    assistant_movement_recorder: AssistantMovementRecorder = MovementsMovementRecorder(
        create_movement=create_movement_use_case,
    )
    assistant_tool_registry = ToolRegistry(
        accounts=assistant_accounts_reader,
        movements=assistant_movements_reader,
        budgets=assistant_budgets_reader,
        goals=assistant_goals_reader,
        debts=assistant_debts_reader,
        subscriptions=assistant_subscriptions_reader,
        categories=assistant_categories_reader,
    )
    assistant_plan_limits = PlanLimits(
        registrations_free=settings.assistant_registrations_free_limit,
        registrations_plus=settings.assistant_registrations_plus_limit,
        messages_free=settings.assistant_messages_free_limit,
        messages_plus=settings.assistant_messages_plus_limit,
        message_grace=settings.assistant_message_grace,
    )
    assistant_pricing = ModelPricing(
        input_usd_per_mtok=settings.anthropic_input_usd_per_mtok,
        output_usd_per_mtok=settings.anthropic_output_usd_per_mtok,
    )

    create_budget_use_case = CreateBudgetUseCase(
        budget_repository=budget_repository,
        category_reader=budget_category_reader,
        category_free_limit=settings.budget_categories_free_limit,
    )
    update_budget_use_case = UpdateBudgetUseCase(budget_repository=budget_repository)
    contribute_use_case = ContributeUseCase(
        goal_repository=goal_repository,
        funds_reader=goal_funds_reader,
        transfer_recorder=goal_transfer_recorder,
    )
    assistant_budget_writer: BudgetWriter = BudgetsBudgetWriter(
        create_budget=create_budget_use_case,
        update_budget=update_budget_use_case,
    )
    assistant_goal_contributor: GoalContributor = GoalsGoalContributor(
        contribute_use_case=contribute_use_case,
    )

    compose_monthly_summary_use_case = ComposeMonthlySummaryUseCase(
        outputs=assistant_agent_outputs,
        movements_reader=assistant_movements_reader,
        budgets_reader=assistant_budgets_reader,
        goals_reader=assistant_goals_reader,
        categories_reader=assistant_categories_reader,
        agent_model=assistant_agent_model,
        action_log=assistant_action_log,
        clock=clock,
        pricing=assistant_pricing,
        model_name=settings.anthropic_model,
        category_caps_free_limit=settings.budget_categories_free_limit,
    )

    compose_weekly_review_use_case = ComposeWeeklyReviewUseCase(
        outputs=assistant_agent_outputs,
        movements_reader=assistant_movements_reader,
        budgets_reader=assistant_budgets_reader,
        goals_reader=assistant_goals_reader,
        categories_reader=assistant_categories_reader,
        subscriptions_reader=assistant_subscriptions_reader,
        agent_model=assistant_agent_model,
        action_log=assistant_action_log,
        clock=clock,
        pricing=assistant_pricing,
        model_name=settings.anthropic_model,
        treat_slack_fraction=settings.assistant_treat_slack_fraction,
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
        list_categories_use_case=list_categories_use_case,
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
        get_daily_spend_use_case=get_daily_spend_use_case,
        get_goal_funds_use_case=get_goal_funds_use_case,
        budget_repository=budget_repository,
        budget_spend_reader=budget_spend_reader,
        budget_category_reader=budget_category_reader,
        get_budgets_snapshot_use_case=get_budgets_snapshot_use_case,
        get_global_cap_use_case=get_global_cap_use_case,
        create_budget_use_case=create_budget_use_case,
        update_budget_use_case=update_budget_use_case,
        delete_budget_use_case=DeleteBudgetUseCase(budget_repository=budget_repository),
        debt_repository=debt_repository,
        counterparty_repository=counterparty_repository,
        event_repository=event_repository,
        get_debts_snapshot_use_case=get_debts_snapshot_use_case,
        get_debt_totals_use_case=get_debt_totals_use_case,
        create_debt_use_case=CreateDebtUseCase(
            debt_repository=debt_repository,
            counterparty_resolver=counterparty_resolver,
        ),
        create_shared_event_use_case=CreateSharedEventUseCase(
            debt_repository=debt_repository,
            event_repository=event_repository,
            counterparty_repository=counterparty_repository,
            counterparty_resolver=counterparty_resolver,
            unit_of_work=unit_of_work,
            snapshot=get_debts_snapshot_use_case,
        ),
        update_debt_use_case=UpdateDebtUseCase(debt_repository=debt_repository),
        delete_debt_use_case=DeleteDebtUseCase(
            debt_repository=debt_repository,
            event_repository=event_repository,
        ),
        add_payment_use_case=AddPaymentUseCase(debt_repository=debt_repository),
        remove_payment_use_case=RemovePaymentUseCase(debt_repository=debt_repository),
        goal_repository=goal_repository,
        goal_funds_reader=goal_funds_reader,
        goal_transfer_recorder=goal_transfer_recorder,
        get_goals_snapshot_use_case=get_goals_snapshot_use_case,
        get_top_goal_use_case=get_top_goal_use_case,
        create_goal_use_case=CreateGoalUseCase(
            goal_repository=goal_repository,
            active_free_limit=settings.goals_active_free_limit,
        ),
        update_goal_use_case=UpdateGoalUseCase(
            goal_repository=goal_repository,
            funds_reader=goal_funds_reader,
            active_free_limit=settings.goals_active_free_limit,
        ),
        delete_goal_use_case=DeleteGoalUseCase(
            goal_repository=goal_repository,
            funds_reader=goal_funds_reader,
        ),
        contribute_use_case=contribute_use_case,
        withdraw_use_case=WithdrawUseCase(
            goal_repository=goal_repository,
            funds_reader=goal_funds_reader,
            transfer_recorder=goal_transfer_recorder,
        ),
        subscription_repository=subscription_repository,
        subscription_source_reader=subscription_source_reader,
        subscription_category_reader=subscription_category_reader,
        subscription_references=subscription_references,
        list_subscriptions_use_case=list_subscriptions_use_case,
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
        debt_totals_reader=debt_totals_reader,
        top_goal_reader=top_goal_reader,
        chat_message_repository=chat_message_repository,
        movement_draft_repository=movement_draft_repository,
        assistant_usage_counters=assistant_usage_counters,
        assistant_insight_dismissals=assistant_insight_dismissals,
        assistant_agent_outputs=assistant_agent_outputs,
        assistant_users_reader=assistant_users_reader,
        assistant_budget_writer=assistant_budget_writer,
        assistant_goal_contributor=assistant_goal_contributor,
        assistant_action_log=assistant_action_log,
        assistant_agent_model=assistant_agent_model,
        assistant_accounts_reader=assistant_accounts_reader,
        assistant_movements_reader=assistant_movements_reader,
        assistant_budgets_reader=assistant_budgets_reader,
        assistant_goals_reader=assistant_goals_reader,
        assistant_debts_reader=assistant_debts_reader,
        assistant_subscriptions_reader=assistant_subscriptions_reader,
        assistant_categories_reader=assistant_categories_reader,
        assistant_movement_recorder=assistant_movement_recorder,
        assistant_tool_registry=assistant_tool_registry,
        send_chat_message_use_case=SendChatMessageUseCase(
            agent_model=assistant_agent_model,
            tool_registry=assistant_tool_registry,
            chat_messages=chat_message_repository,
            drafts=movement_draft_repository,
            usage_counters=assistant_usage_counters,
            action_log=assistant_action_log,
            unit_of_work=unit_of_work,
            accounts_reader=assistant_accounts_reader,
            categories_reader=assistant_categories_reader,
            plan_limits=assistant_plan_limits,
            pricing=assistant_pricing,
            model_name=settings.anthropic_model,
            history_window=settings.assistant_history_window,
            max_tool_iterations=settings.assistant_max_tool_iterations,
        ),
        parse_capture_use_case=ParseCaptureUseCase(
            agent_model=assistant_agent_model,
            tool_registry=assistant_tool_registry,
            drafts=movement_draft_repository,
            usage_counters=assistant_usage_counters,
            action_log=assistant_action_log,
            unit_of_work=unit_of_work,
            accounts_reader=assistant_accounts_reader,
            categories_reader=assistant_categories_reader,
            plan_limits=assistant_plan_limits,
            pricing=assistant_pricing,
            model_name=settings.anthropic_model,
        ),
        get_chat_history_use_case=GetChatHistoryUseCase(
            chat_messages=chat_message_repository,
            drafts=movement_draft_repository,
        ),
        confirm_draft_use_case=ConfirmDraftUseCase(
            drafts=movement_draft_repository,
            movement_recorder=assistant_movement_recorder,
        ),
        discard_draft_use_case=DiscardDraftUseCase(
            drafts=movement_draft_repository,
        ),
        get_assistant_usage_use_case=GetUsageUseCase(
            usage_counters=assistant_usage_counters,
            plan_limits=assistant_plan_limits,
        ),
        get_assistant_feed_use_case=GetAssistantFeedUseCase(
            budgets_reader=assistant_budgets_reader,
            subscriptions_reader=assistant_subscriptions_reader,
            movements_reader=assistant_movements_reader,
            categories_reader=assistant_categories_reader,
            dismissals=assistant_insight_dismissals,
            outputs=assistant_agent_outputs,
        ),
        dismiss_insight_use_case=DismissInsightUseCase(
            dismissals=assistant_insight_dismissals,
        ),
        compose_monthly_summary_use_case=compose_monthly_summary_use_case,
        run_monthly_summaries_use_case=RunMonthlySummariesUseCase(
            users_reader=assistant_users_reader,
            compose=compose_monthly_summary_use_case,
            clock=clock,
        ),
        apply_play_use_case=ApplyPlayUseCase(
            outputs=assistant_agent_outputs,
            budget_writer=assistant_budget_writer,
            goal_contributor=assistant_goal_contributor,
            clock=clock,
        ),
        compose_weekly_review_use_case=compose_weekly_review_use_case,
        run_weekly_reviews_use_case=RunWeeklyReviewsUseCase(
            users_reader=assistant_users_reader,
            compose=compose_weekly_review_use_case,
            clock=clock,
            audience=settings.assistant_weekly_review_audience,
        ),
        list_outputs_use_case=ListOutputsUseCase(outputs=assistant_agent_outputs),
        get_output_use_case=GetOutputUseCase(outputs=assistant_agent_outputs),
        mark_output_read_use_case=MarkOutputReadUseCase(
            outputs=assistant_agent_outputs,
            clock=clock,
        ),
        dismiss_output_use_case=DismissOutputUseCase(
            outputs=assistant_agent_outputs,
            clock=clock,
        ),
        get_home_overview_use_case=GetHomeOverviewUseCase(
            balance_reader=balance_reader,
            movement_summary_reader=movement_summary_reader,
            upcoming_charges_reader=upcoming_charges_reader,
            budget_reader=budget_cap_reader,
            debt_reader=debt_totals_reader,
            goal_reader=top_goal_reader,
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
