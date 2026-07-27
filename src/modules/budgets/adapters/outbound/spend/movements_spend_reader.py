from dataclasses import dataclass
from uuid import UUID

from src.modules.budgets.application.ports.spend_reader import (
    CategorySpendView,
    MerchantSpendView,
)
from src.modules.movements.application.dto.movement_summary import SummarizeMovementsInputDTO
from src.modules.movements.application.dto.top_merchants import TopMerchantsInputDTO
from src.modules.movements.application.use_cases.get_top_merchants import GetTopMerchantsUseCase
from src.modules.movements.application.use_cases.summarize_movements import (
    SummarizeMovementsUseCase,
)


@dataclass
class MovementsSpendReader:
    """`SpendReader` backed by the movements module.

    Talks to its use cases, never to its documents: the aggregation lives with the
    collection that owns it and this is only the translation into what a cap needs. It is
    also the seam that keeps `budgets` from importing `movements` — the hexagon knows
    nothing about this file.
    """

    summarize_movements: SummarizeMovementsUseCase
    get_top_merchants: GetTopMerchantsUseCase

    async def spent(self, user_id: UUID, date_from: str, date_to: str) -> int:
        output = await self.summarize_movements.execute(
            SummarizeMovementsInputDTO(user_id=user_id, date_from=date_from, date_to=date_to)
        )
        return output.expense_total

    async def by_category(
        self, user_id: UUID, date_from: str, date_to: str
    ) -> list[CategorySpendView]:
        output = await self.summarize_movements.execute(
            SummarizeMovementsInputDTO(user_id=user_id, date_from=date_from, date_to=date_to)
        )
        return [
            CategorySpendView(category_id=spend.category_id, spent=spend.spent, count=spend.count)
            for spend in output.by_category
        ]

    async def top_merchants(
        self,
        user_id: UUID,
        date_from: str,
        date_to: str,
        category_id: str | None,
        limit: int,
    ) -> list[MerchantSpendView]:
        output = await self.get_top_merchants.execute(
            TopMerchantsInputDTO(
                user_id=user_id,
                date_from=date_from,
                date_to=date_to,
                category_id=category_id,
                limit=limit,
            )
        )
        return [
            MerchantSpendView(label=merchant.label, spent=merchant.spent, count=merchant.count)
            for merchant in output.merchants
        ]
