from uuid import UUID

from src.modules.budgets.adapters.outbound.persistence.documents.budget_document import (
    BudgetDocument,
)
from src.modules.budgets.adapters.outbound.persistence.mappers.budget_mapper import BudgetMapper
from src.modules.budgets.domain.entities.budget import Budget
from src.shared.adapters.outbound.persistence.mongo import current_session


class MongoBudgetRepository:
    """Beanie/Mongo implementation of `BudgetRepository`.

    Every read is tenant-scoped, and the `(user_id, scope, category_id)` unique index
    serves all of them: the user's list is its prefix, and the two `find_*` below hit it
    exactly.
    """

    async def list_by_user(self, user_id: UUID) -> list[Budget]:
        docs = await BudgetDocument.find({"user_id": str(user_id)}).to_list()
        return [BudgetMapper.to_domain(doc) for doc in docs]

    async def find(self, user_id: UUID, budget_id: str) -> Budget | None:
        doc = await BudgetDocument.find_one(
            BudgetDocument.id == budget_id,
            BudgetDocument.user_id == str(user_id),
        )
        return BudgetMapper.to_domain(doc) if doc else None

    async def find_global(self, user_id: UUID) -> Budget | None:
        doc = await BudgetDocument.find_one({"user_id": str(user_id), "scope": "global"})
        return BudgetMapper.to_domain(doc) if doc else None

    async def find_for_category(self, user_id: UUID, category_id: str) -> Budget | None:
        doc = await BudgetDocument.find_one(
            {"user_id": str(user_id), "scope": "category", "category_id": category_id}
        )
        return BudgetMapper.to_domain(doc) if doc else None

    async def save(self, budget: Budget) -> None:
        session = current_session()
        existing = await BudgetDocument.get(budget.id, session=session)
        if existing is None:
            await BudgetMapper.to_document(budget).insert(session=session)
            return
        # Only the number and its stamp can change: scope and category identify the cap.
        existing.target = budget.target
        existing.since = budget.since
        await existing.save(session=session)

    async def delete(self, user_id: UUID, budget_id: str) -> None:
        doc = await BudgetDocument.find_one(
            BudgetDocument.id == budget_id,
            BudgetDocument.user_id == str(user_id),
        )
        if doc is not None:
            await doc.delete(session=current_session())
