from dataclasses import dataclass
from uuid import UUID

from src.modules.assistant.application.ports.goals_reader import GoalView
from src.modules.goals.application.use_cases.get_goals_snapshot import GetGoalsSnapshotUseCase


@dataclass
class GoalsGoalsReader:
    """`GoalsReader` backed by goals — same derivations as the Metas screen."""

    get_goals_snapshot: GetGoalsSnapshotUseCase

    async def snapshot(self, user_id: UUID, currency: str, today: str) -> tuple[GoalView, ...]:
        output = await self.get_goals_snapshot.execute_for(user_id, currency, today)
        return tuple(
            GoalView(
                id=g.id,
                name=g.name,
                target=g.target,
                saved=g.saved,
                pct=g.pct,
                achieved=g.achieved,
                archived=g.archived,
                target_date=g.target_date,
                projected_on=g.projected_on,
                needed_per_month=g.needed_per_month,
            )
            for g in output.goals
        )
