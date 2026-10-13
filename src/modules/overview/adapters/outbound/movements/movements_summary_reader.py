from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from src.modules.movements.application.dto.daily_spend import DailySpendInputDTO
from src.modules.movements.application.dto.list_movements import ListMovementsInputDTO
from src.modules.movements.application.dto.movement_summary import (
    SummarizeMovementsInputDTO,
)
from src.modules.movements.application.use_cases.get_daily_spend import GetDailySpendUseCase
from src.modules.movements.application.use_cases.list_movements import ListMovementsUseCase
from src.modules.movements.application.use_cases.summarize_movements import (
    SummarizeMovementsUseCase,
)
from src.modules.overview.application.ports.movement_summary_reader import (
    CategorySpendView,
    DaySpendView,
    PeriodSummary,
    RecentMovementView,
)


@dataclass
class MovementsSummaryReader:
    """`MovementSummaryReader` backed by the movements module.

    Talks to its use cases, never to its documents: the aggregation lives with the
    collection that owns it and this is only the translation into what Home needs.
    """

    summarize_movements: SummarizeMovementsUseCase
    list_movements: ListMovementsUseCase
    get_daily_spend: GetDailySpendUseCase

    async def summary(self, user_id: UUID, date_from: str, date_to: str) -> PeriodSummary:
        output = await self.summarize_movements.execute(
            SummarizeMovementsInputDTO(user_id=user_id, date_from=date_from, date_to=date_to)
        )
        return PeriodSummary(
            expense_total=output.expense_total,
            income_total=output.income_total,
            count=output.count,
            by_category=tuple(
                CategorySpendView(
                    category_id=spend.category_id, spent=spend.spent, count=spend.count
                )
                for spend in output.by_category
            ),
        )

    async def recent(self, user_id: UUID, limit: int) -> list[RecentMovementView]:
        output = await self.list_movements.execute(
            ListMovementsInputDTO(user_id=user_id, limit=limit)
        )
        return [
            RecentMovementView(
                id=movement.id,
                type=movement.type,
                description=movement.description,
                amount=movement.amount,
                currency=movement.currency,
                source_type=movement.source_type,
                source_id=movement.source_id,
                destination_type=movement.destination_type,
                destination_id=movement.destination_id,
                category_id=movement.category_id,
                occurred_on=movement.occurred_on,
                captured_via=movement.captured_via,
                subscription_id=movement.subscription_id,
            )
            for movement in output.movements
        ]

    async def spend_by_day(
        self, user_id: UUID, date_from: str, date_to: str
    ) -> tuple[DaySpendView, ...]:
        output = await self.get_daily_spend.execute(
            DailySpendInputDTO(user_id=user_id, date_from=date_from, date_to=date_to)
        )
        spent = {day.day: day.spent for day in output.days}

        # The gaps are the point: a day the user spent nothing is a short bar, not a
        # missing one, and the row only reads as a calendar if every day has a slot.
        days: list[DaySpendView] = []
        cursor = date.fromisoformat(date_from)
        last = date.fromisoformat(date_to)
        while cursor <= last:
            key = cursor.isoformat()
            days.append(DaySpendView(day=key, spent=spent.get(key, 0)))
            cursor += timedelta(days=1)
        return tuple(days)
