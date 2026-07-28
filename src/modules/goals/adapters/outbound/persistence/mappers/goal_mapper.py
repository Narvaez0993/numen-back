from uuid import UUID

from src.modules.goals.adapters.outbound.persistence.documents.goal_document import (
    GoalDocument,
)
from src.modules.goals.domain.entities.goal import Goal


class GoalMapper:
    @staticmethod
    def to_domain(doc: GoalDocument) -> Goal:
        return Goal(
            id=doc.id,
            user_id=UUID(doc.user_id),
            name=doc.name,
            icon=doc.icon,
            color=doc.color,
            target=doc.target,
            currency=doc.currency,
            target_date=doc.target_date,
            archived_at=doc.archived_at,
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(goal: Goal) -> GoalDocument:
        return GoalDocument(
            id=goal.id,
            user_id=str(goal.user_id),
            name=goal.name,
            icon=goal.icon,
            color=goal.color,
            target=goal.target,
            currency=goal.currency,
            target_date=goal.target_date,
            archived_at=goal.archived_at,
            created_at=goal.created_at,
        )
