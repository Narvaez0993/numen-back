from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from src.modules.goals.application.ports.funds_reader import PocketFunds
from src.modules.goals.application.ports.transfer_recorder import RecordedTransfer
from src.modules.goals.domain.entities.goal import Goal

FIXED_NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=UTC)
TODAY = "2026-07-27"
CURRENCY = "COP"
FREE_ACTIVE_LIMIT = 1


class FakeGoalRepository:
    def __init__(self, goals: list[Goal] | None = None) -> None:
        self.goals = list(goals or [])

    async def list_by_user(self, user_id: UUID) -> list[Goal]:
        return [g for g in self.goals if g.user_id == user_id]

    async def find(self, user_id: UUID, goal_id: str) -> Goal | None:
        for goal in self.goals:
            if goal.id == goal_id and goal.user_id == user_id:
                return goal
        return None

    async def save(self, goal: Goal) -> None:
        for index, existing in enumerate(self.goals):
            if existing.id == goal.id:
                self.goals[index] = goal
                return
        self.goals.append(goal)

    async def delete(self, user_id: UUID, goal_id: str) -> None:
        self.goals = [g for g in self.goals if not (g.id == goal_id and g.user_id == user_id)]


class FakeFundsReader:
    """Pocket money by goal id — what the movements aggregation would answer."""

    def __init__(self, funds: dict[str, PocketFunds] | None = None) -> None:
        self.result = funds or {}

    async def funds(self, user_id: UUID) -> dict[str, PocketFunds]:
        return self.result


class FakeTransferRecorder:
    """Records what would become a real transfer movement, for assertions."""

    def __init__(self) -> None:
        self.recorded: list[dict[str, object]] = []

    async def record(
        self,
        *,
        user_id: UUID,
        currency: str,
        description: str,
        amount: int,
        account_id: str,
        goal_id: str,
        direction: Literal["in", "out"],
        occurred_on: str,
    ) -> RecordedTransfer:
        self.recorded.append(
            {
                "user_id": user_id,
                "currency": currency,
                "description": description,
                "amount": amount,
                "account_id": account_id,
                "goal_id": goal_id,
                "direction": direction,
                "occurred_on": occurred_on,
            }
        )
        return RecordedTransfer(movement_id=f"mov-{len(self.recorded)}")


def goal(
    *,
    user_id: UUID,
    name: str = "Viaje a Japón",
    target: int = 12_000_000,
    target_date: str | None = None,
    archived_at: datetime | None = None,
    created_at: datetime = FIXED_NOW,
) -> Goal:
    return Goal(
        id=str(uuid4()),
        user_id=user_id,
        name=name,
        icon="target",
        color="mint",
        target=target,
        currency=CURRENCY,
        target_date=target_date,
        archived_at=archived_at,
        created_at=created_at,
    )


def funds(goal_id: str, saved: int, first_in_on: str | None = "2026-06-01") -> PocketFunds:
    return PocketFunds(goal_id=goal_id, saved=saved, first_in_on=first_in_on)


def new_user_id() -> UUID:
    return uuid4()
