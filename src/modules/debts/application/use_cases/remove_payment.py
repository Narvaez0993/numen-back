from dataclasses import dataclass

from src.modules.debts.application.dto.debt import DebtDTO
from src.modules.debts.application.dto.debt_commands import RemovePaymentInputDTO
from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.debts.domain.errors import DebtNotFoundError, InvalidDebtError


@dataclass
class RemovePaymentUseCase:
    """Undo for a mistyped payment — the same courtesy movements give with delete.

    Removing it can only ever *raise* what is owed, so there is no overpay-style check
    to mirror here.
    """

    debt_repository: DebtRepository

    async def execute(self, input_dto: RemovePaymentInputDTO) -> DebtDTO:
        debt = await self.debt_repository.find(input_dto.user_id, input_dto.debt_id)
        if debt is None:
            raise DebtNotFoundError()
        if all(payment.id != input_dto.payment_id for payment in debt.payments):
            raise InvalidDebtError("That payment does not exist")

        updated = debt.without_payment(input_dto.payment_id)
        await self.debt_repository.save(updated)
        return DebtDTO.from_domain(updated, input_dto.today)
