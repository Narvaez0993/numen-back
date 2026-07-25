from typing import cast
from uuid import UUID

from src.modules.accounts.adapters.outbound.persistence.documents.account_document import (
    AccountDocument,
)
from src.modules.accounts.domain.entities.account import Account, AccountKind


class AccountMapper:
    @staticmethod
    def to_domain(doc: AccountDocument) -> Account:
        return Account(
            id=doc.id,
            user_id=UUID(doc.user_id),
            kind=cast(AccountKind, doc.kind),
            name=doc.name,
            sub=doc.sub,
            icon=doc.icon,
            color=doc.color,
            currency=doc.currency,
            balance=doc.balance,
            initial_balance=doc.initial_balance,
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(account: Account) -> AccountDocument:
        return AccountDocument(
            id=account.id,
            user_id=str(account.user_id),
            kind=account.kind,
            name=account.name,
            sub=account.sub,
            icon=account.icon,
            color=account.color,
            currency=account.currency,
            balance=account.balance,
            initial_balance=account.initial_balance,
            created_at=account.created_at,
        )
