from typing import cast
from uuid import UUID

from src.modules.budgets.adapters.outbound.persistence.documents.budget_document import (
    BudgetDocument,
)
from src.modules.budgets.domain.entities.budget import Budget, Scope


class BudgetMapper:
    @staticmethod
    def to_domain(doc: BudgetDocument) -> Budget:
        return Budget(
            id=doc.id,
            user_id=UUID(doc.user_id),
            scope=cast(Scope, doc.scope),
            category_id=doc.category_id,
            target=doc.target,
            since=doc.since,
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(budget: Budget) -> BudgetDocument:
        return BudgetDocument(
            id=budget.id,
            user_id=str(budget.user_id),
            scope=budget.scope,
            category_id=budget.category_id,
            target=budget.target,
            since=budget.since,
            created_at=budget.created_at,
        )
