from uuid import UUID

from src.modules.accounts.adapters.outbound.persistence.documents.account_document import (
    AccountDocument,
)
from src.modules.accounts.adapters.outbound.persistence.mappers.account_mapper import (
    AccountMapper,
)
from src.modules.accounts.domain.entities.account import Account
from src.shared.adapters.outbound.persistence.mongo import current_session


class MongoAccountRepository:
    """Beanie/Mongo implementation of `AccountRepository`.

    Every query is prefixed by `user_id` and served by the compound index on
    `(user_id, created_at)` declared in `AccountDocument`.
    """

    async def list_by_user(self, user_id: UUID) -> list[Account]:
        docs = (
            await AccountDocument.find(AccountDocument.user_id == str(user_id))
            .sort("+created_at")
            .to_list()
        )
        return [AccountMapper.to_domain(doc) for doc in docs]

    async def find(self, user_id: UUID, account_id: str) -> Account | None:
        doc = await AccountDocument.find_one(
            AccountDocument.id == account_id,
            AccountDocument.user_id == str(user_id),
        )
        return AccountMapper.to_domain(doc) if doc else None

    async def save(self, account: Account) -> None:
        existing = await AccountDocument.get(account.id)
        if existing is None:
            await AccountMapper.to_document(account).insert(session=current_session())
            return
        existing.kind = account.kind
        existing.name = account.name
        existing.sub = account.sub
        existing.icon = account.icon
        existing.color = account.color
        existing.currency = account.currency
        existing.balance = account.balance
        existing.initial_balance = account.initial_balance
        await existing.save(session=current_session())

    async def delete(self, user_id: UUID, account_id: str) -> None:
        doc = await AccountDocument.find_one(
            AccountDocument.id == account_id,
            AccountDocument.user_id == str(user_id),
        )
        if doc is not None:
            await doc.delete(session=current_session())
