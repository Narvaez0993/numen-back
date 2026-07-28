from uuid import UUID

from src.modules.accounts.adapters.outbound.persistence.documents.account_document import (
    AccountDocument,
)
from src.modules.accounts.adapters.outbound.persistence.documents.credit_card_document import (
    CreditCardDocument,
)
from src.modules.debts.adapters.outbound.persistence.documents.debt_document import (
    DebtDocument,
)
from src.modules.goals.adapters.outbound.persistence.documents.goal_document import (
    GoalDocument,
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
from src.shared.adapters.outbound.persistence.mongo import current_session


class SourcesCurrencyScope:
    """`CurrencyScope` over everything that carries a currency.

    **History is a movement**: something that already happened, at an amount the user
    typed on a day. Accounts, cards and subscriptions are *setup* — a balance the user
    entered minutes ago while picking the wrong currency is meant to be corrected, and
    blocking on it would trap the most common case ("I just finished onboarding and
    chose wrong").

    Writes go through targeted `update_many` on the documents rather than each
    module's repository: this only re-labels a field, and loading, mapping and saving
    every entity to change one string would be slower and no safer.
    """

    async def has_history(self, user_id: UUID) -> bool:
        return await MovementDocument.find({"user_id": str(user_id)}).count() > 0

    async def restamp(self, user_id: UUID, currency: str) -> None:
        session = current_session()
        criteria = {"user_id": str(user_id)}
        update = {"$set": {"currency": currency}}
        for document in (
            AccountDocument,
            CreditCardDocument,
            SubscriptionDocument,
            SubscriptionChargeDocument,
            # Debts and goals are setup too: a ledger typed in the wrong currency is
            # the same onboarding mistake. Payments and events carry no currency of
            # their own.
            DebtDocument,
            GoalDocument,
        ):
            await document.find(criteria).update(update, session=session)
