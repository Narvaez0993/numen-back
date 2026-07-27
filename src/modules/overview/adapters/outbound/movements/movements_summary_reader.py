from dataclasses import dataclass
from uuid import UUID

from src.modules.movements.application.dto.list_movements import ListMovementsInputDTO
from src.modules.movements.application.dto.movement_summary import (
    SummarizeMovementsInputDTO,
)
from src.modules.movements.application.use_cases.list_movements import ListMovementsUseCase
from src.modules.movements.application.use_cases.summarize_movements import (
    SummarizeMovementsUseCase,
)
from src.modules.overview.application.ports.movement_summary_reader import (
    CategorySpendView,
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
