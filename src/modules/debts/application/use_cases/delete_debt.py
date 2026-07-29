from dataclasses import dataclass

from src.modules.debts.application.dto.debt_commands import DeleteDebtInputDTO
from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.debts.application.ports.event_repository import EventRepository
from src.modules.debts.domain.errors import DebtNotFoundError


@dataclass
class DeleteDebtUseCase:
    """Forgets a debt. Nothing else moves — it never held money.

    If it was the last debt of a shared event, the event goes with it: an event is
    only the grouping of its debts, and an empty group is not a thing the screen
    should ever have to render.
    """

    debt_repository: DebtRepository
    event_repository: EventRepository

    async def execute(self, input_dto: DeleteDebtInputDTO) -> None:
        debt = await self.debt_repository.find(input_dto.user_id, input_dto.debt_id)
        if debt is None:
            raise DebtNotFoundError()

        await self.debt_repository.delete(input_dto.user_id, input_dto.debt_id)

        if debt.event_id is not None:
            siblings = await self.debt_repository.list_by_event(input_dto.user_id, debt.event_id)
            if not siblings:
                await self.event_repository.delete(input_dto.user_id, debt.event_id)
