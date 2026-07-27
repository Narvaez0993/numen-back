from dataclasses import dataclass
from uuid import UUID

from src.modules.accounts.application.ports.account_repository import AccountRepository
from src.modules.accounts.application.ports.credit_card_repository import (
    CreditCardRepository,
)
from src.modules.subscriptions.application.ports.source_reader import SourceSnapshot
from src.modules.subscriptions.domain.entities.subscription import SourceRef


@dataclass
class AccountsSourceReader:
    """`SourceReader` backed by the accounts module.

    The anti-corruption seam: it reads through accounts' **ports**, never its
    documents, and it only reads — moving money on a charge is the movements
    module's job, which is where the cash-basis rule lives.
    """

    account_repository: AccountRepository
    credit_card_repository: CreditCardRepository

    async def find(self, user_id: UUID, ref: SourceRef) -> SourceSnapshot | None:
        if ref.type == "account":
            account = await self.account_repository.find(user_id, ref.id)
            if account is None:
                return None
            return SourceSnapshot(ref=ref, currency=account.currency)

        card = await self.credit_card_repository.find(user_id, ref.id)
        if card is None:
            return None
        return SourceSnapshot(ref=ref, currency=card.currency)
