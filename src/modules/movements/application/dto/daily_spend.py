from uuid import UUID

from pydantic import BaseModel

from src.modules.movements.application.ports.movement_repository import DaySpend


class DailySpendInputDTO(BaseModel):
    user_id: UUID
    date_from: str
    date_to: str


class DaySpendDTO(BaseModel):
    day: str
    spent: int
    count: int

    @classmethod
    def from_domain(cls, day: DaySpend) -> "DaySpendDTO":
        return cls(day=day.day, spent=day.spent, count=day.count)


class DailySpendOutputDTO(BaseModel):
    """The month's rhythm, day by day. Days without spending are absent — the
    consumer decides whether that means zero or "not yet". Amounts in the minor
    unit of the user's currency."""

    date_from: str
    date_to: str
    days: list[DaySpendDTO]
