from dataclasses import dataclass
from uuid import UUID

from src.modules.debts.application.dto.debt_commands import DebtTotalsInputDTO
from src.modules.debts.application.use_cases.get_debt_totals import GetDebtTotalsUseCase
from src.modules.overview.application.ports.debt_reader import DebtTotalsView


@dataclass
class DebtsDebtReader:
    """`DebtReader` backed by the debts module.

    Calls the narrow use case, not the screen's snapshot: Home needs two totals and a
    count, none of the people or events behind them. The totals come from the same
    pure derivations the Deudas screen uses, so the two can never disagree.
    """

    get_debt_totals: GetDebtTotalsUseCase

    async def totals(self, user_id: UUID) -> DebtTotalsView:
        output = await self.get_debt_totals.execute(DebtTotalsInputDTO(user_id=user_id))
        return DebtTotalsView(
            i_owe=output.i_owe,
            owed_to_me=output.owed_to_me,
            open_count=output.open_count,
        )
