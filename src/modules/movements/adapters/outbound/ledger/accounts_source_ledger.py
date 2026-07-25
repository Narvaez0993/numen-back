from dataclasses import dataclass
from uuid import UUID

from src.modules.accounts.adapters.outbound.persistence.documents.account_document import (
    AccountDocument,
)
from src.modules.accounts.adapters.outbound.persistence.documents.credit_card_document import (
    CreditCardDocument,
)
from src.modules.accounts.application.ports.account_repository import AccountRepository
from src.modules.accounts.application.ports.credit_card_repository import (
    CreditCardRepository,
)
from src.modules.movements.application.ports.source_ledger import SourceSnapshot
from src.modules.movements.domain.entities.movement import SourceRef
from src.shared.adapters.outbound.persistence.mongo import current_session


@dataclass
class AccountsSourceLedger:
    """`SourceLedger` backed by the accounts module.

    The anti-corruption layer between the two modules: it reads through accounts'
    *ports* and writes with a targeted `$inc`.

    Why `$inc` and not a read-modify-write through the entity: a movement must move
    only the **current** balance and never the reconciliation anchor
    (`initial_balance` / `initial_debt`), and an increment is immune to lost
    updates. Sign flips for a card because a positive delta always means "your
    position improved", and for a liability that is less debt.
    """

    account_repository: AccountRepository
    credit_card_repository: CreditCardRepository

    async def find(self, user_id: UUID, ref: SourceRef) -> SourceSnapshot | None:
        if ref.type == "account":
            account = await self.account_repository.find(user_id, ref.id)
            if account is None:
                return None
            return SourceSnapshot(ref=ref, type="account", currency=account.currency)

        card = await self.credit_card_repository.find(user_id, ref.id)
        if card is None:
            return None
        return SourceSnapshot(ref=ref, type="credit_card", currency=card.currency)

    async def apply_delta(self, user_id: UUID, ref: SourceRef, delta: int) -> None:
        session = current_session()
        if ref.type == "account":
            await AccountDocument.find_one(
                AccountDocument.id == ref.id,
                AccountDocument.user_id == str(user_id),
            ).update({"$inc": {"balance": delta}}, session=session)
            return
        await CreditCardDocument.find_one(
            CreditCardDocument.id == ref.id,
            CreditCardDocument.user_id == str(user_id),
        ).update({"$inc": {"debt": -delta}}, session=session)
