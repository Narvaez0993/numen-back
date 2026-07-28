from uuid import UUID

from src.modules.goals.adapters.outbound.persistence.documents.goal_document import (
    GoalDocument,
)
from src.modules.goals.adapters.outbound.persistence.mappers.goal_mapper import GoalMapper
from src.modules.goals.domain.entities.goal import Goal
from src.shared.adapters.outbound.persistence.mongo import current_session


class MongoGoalRepository:
    """Beanie/Mongo implementation of `GoalRepository`. Every read is tenant-scoped."""

    async def list_by_user(self, user_id: UUID) -> list[Goal]:
        docs = await GoalDocument.find({"user_id": str(user_id)}).to_list()
        return [GoalMapper.to_domain(doc) for doc in docs]

    async def find(self, user_id: UUID, goal_id: str) -> Goal | None:
        doc = await GoalDocument.find_one(
            GoalDocument.id == goal_id,
            GoalDocument.user_id == str(user_id),
        )
        return GoalMapper.to_domain(doc) if doc else None

    async def save(self, goal: Goal) -> None:
        session = current_session()
        existing = await GoalDocument.get(goal.id, session=session)
        if existing is None:
            await GoalMapper.to_document(goal).insert(session=session)
            return
        fresh = GoalMapper.to_document(goal)
        existing.name = fresh.name
        existing.icon = fresh.icon
        existing.color = fresh.color
        existing.target = fresh.target
        existing.currency = fresh.currency
        existing.target_date = fresh.target_date
        existing.archived_at = fresh.archived_at
        await existing.save(session=session)

    async def delete(self, user_id: UUID, goal_id: str) -> None:
        doc = await GoalDocument.find_one(
            GoalDocument.id == goal_id,
            GoalDocument.user_id == str(user_id),
        )
        if doc is not None:
            await doc.delete(session=current_session())
