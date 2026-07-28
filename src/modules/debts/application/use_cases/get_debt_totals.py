from dataclasses import dataclass

from src.modules.debts.application.dto.debt import DebtTotalsDTO
from src.modules.debts.application.dto.debt_commands import DebtTotalsInputDTO
from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.debts.domain import status as debt_status


@dataclass
class GetDebtTotalsUseCase:
    """The hero's read: what the user owes people and what people owe them.

    It loads the list and derives with the same functions the snapshot uses — a user's
    debts are dozens, and one code path is what guarantees Home and the Deudas screen
    can never show different numbers for the same day.
    """

    debt_repository: DebtRepository

    async def execute(self, input_dto: DebtTotalsInputDTO) -> DebtTotalsDTO:
        debts = await self.debt_repository.list_by_user(input_dto.user_id)

        i_owe = 0
        owed_to_me = 0
        open_count = 0
        for debt in debts:
            left = debt_status.remaining(debt)
            if left == 0:
                continue
            open_count += 1
            if debt.direction == "outgoing":
                i_owe += left
            else:
                owed_to_me += left

        return DebtTotalsDTO(i_owe=i_owe, owed_to_me=owed_to_me, open_count=open_count)
