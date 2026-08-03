"""Every Beanie document, in one list — the app and the worker both register it.

They used to keep separate lists and the worker's drifted 9 documents behind;
a cron job would then touch a collection Beanie never initialized. One list,
zero drift. Lives in `core` because only the composition root may see every
module at once.
"""

from beanie import Document

from src.modules.accounts.adapters.outbound.persistence.documents.account_document import (
    AccountDocument,
)
from src.modules.accounts.adapters.outbound.persistence.documents.credit_card_document import (
    CreditCardDocument,
)
from src.modules.assistant.adapters.outbound.persistence.documents.action_log_document import (
    AIActionLogDocument,
)
from src.modules.assistant.adapters.outbound.persistence.documents.agent_output_document import (
    AgentOutputDocument,
)
from src.modules.assistant.adapters.outbound.persistence.documents.chat_message_document import (
    ChatMessageDocument,
)
from src.modules.assistant.adapters.outbound.persistence.documents.dismissal_document import (
    InsightDismissalDocument,
)
from src.modules.assistant.adapters.outbound.persistence.documents.movement_draft_document import (
    MovementDraftDocument,
)
from src.modules.assistant.adapters.outbound.persistence.documents.usage_counter_document import (
    AIUsageCounterDocument,
)
from src.modules.auth.adapters.outbound.persistence.documents.email_verification_code_document import (  # noqa: E501
    EmailVerificationCodeDocument,
)
from src.modules.auth.adapters.outbound.persistence.documents.refresh_token_document import (
    RefreshTokenDocument,
)
from src.modules.auth.adapters.outbound.persistence.documents.user_document import UserDocument
from src.modules.budgets.adapters.outbound.persistence.documents.budget_document import (
    BudgetDocument,
)
from src.modules.categories.adapters.outbound.persistence.documents.category_document import (
    CategoryDocument,
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
from src.modules.goals.adapters.outbound.persistence.documents.goal_document import (
    GoalDocument,
)
from src.modules.movements.adapters.outbound.persistence.documents.idempotency_key_document import (
    IdempotencyKeyDocument,
)
from src.modules.movements.adapters.outbound.persistence.documents.movement_document import (
    MovementDocument,
)
from src.modules.subscriptions.adapters.outbound.persistence.documents.subscription_charge_document import (  # noqa: E501
    SubscriptionChargeDocument,
)
from src.modules.subscriptions.adapters.outbound.persistence.documents.subscription_document import (  # noqa: E501
    SubscriptionDocument,
)

ALL_DOCUMENTS: list[type[Document]] = [
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
    InsightDismissalDocument,
    AgentOutputDocument,
]
