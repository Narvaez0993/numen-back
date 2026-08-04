from dataclasses import dataclass
from uuid import UUID

from src.modules.assistant.application.ports.movements_reader import (
    CategorySpendView,
    DaySpendView,
    MerchantView,
    MovementView,
    PeriodSummaryView,
)
from src.modules.movements.application.dto.daily_spend import DailySpendInputDTO
from src.modules.movements.application.dto.list_movements import ListMovementsInputDTO
from src.modules.movements.application.dto.movement_summary import SummarizeMovementsInputDTO
from src.modules.movements.application.dto.top_merchants import OverallTopMerchantsInputDTO
from src.modules.movements.application.use_cases.get_daily_spend import GetDailySpendUseCase
from src.modules.movements.application.use_cases.get_overall_top_merchants import (
    GetOverallTopMerchantsUseCase,
)
from src.modules.movements.application.use_cases.list_movements import ListMovementsUseCase
from src.modules.movements.application.use_cases.summarize_movements import (
    SummarizeMovementsUseCase,
)


@dataclass
class MovementsMovementsReader:
    """`MovementsReader` backed by movements — four questions, one source."""

    summarize_movements: SummarizeMovementsUseCase
    list_movements: ListMovementsUseCase
    # The overall variant on purpose: this reader's `top_merchants` means the
    # whole period, and the sibling use case's `category_id=None` means the
    # unclassified bucket — wiring that one here ranked "Vario" over Éxito.
    get_top_merchants: GetOverallTopMerchantsUseCase
    get_daily_spend: GetDailySpendUseCase

    async def summary(self, user_id: UUID, date_from: str, date_to: str) -> PeriodSummaryView:
        output = await self.summarize_movements.execute(
            SummarizeMovementsInputDTO(user_id=user_id, date_from=date_from, date_to=date_to)
        )
        return PeriodSummaryView(
            date_from=output.date_from,
            date_to=output.date_to,
            expense_total=output.expense_total,
            income_total=output.income_total,
            count=output.count,
            by_category=tuple(
                CategorySpendView(category_id=c.category_id, spent=c.spent, count=c.count)
                for c in output.by_category
            ),
        )

    async def recent(self, user_id: UUID, limit: int) -> tuple[MovementView, ...]:
        output = await self.list_movements.execute(
            ListMovementsInputDTO(user_id=user_id, limit=limit)
        )
        return tuple(
            MovementView(
                id=m.id,
                type=m.type,
                description=m.description,
                amount=m.amount,
                occurred_on=m.occurred_on,
                category_id=m.category_id,
            )
            for m in output.movements
        )

    async def top_merchants(
        self, user_id: UUID, date_from: str, date_to: str, limit: int
    ) -> tuple[MerchantView, ...]:
        output = await self.get_top_merchants.execute(
            OverallTopMerchantsInputDTO(
                user_id=user_id, date_from=date_from, date_to=date_to, limit=limit
            )
        )
        return tuple(
            MerchantView(label=m.label, spent=m.spent, count=m.count) for m in output.merchants
        )

    async def spend_by_day(
        self, user_id: UUID, date_from: str, date_to: str
    ) -> tuple[DaySpendView, ...]:
        output = await self.get_daily_spend.execute(
            DailySpendInputDTO(user_id=user_id, date_from=date_from, date_to=date_to)
        )
        return tuple(DaySpendView(day=d.day, spent=d.spent, count=d.count) for d in output.days)
