from dataclasses import dataclass

from src.modules.debts.application.dto.debt import DebtDTO
from src.modules.debts.application.dto.debt_commands import AddPaymentInputDTO
from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.debts.domain import status as debt_status
from src.modules.debts.domain.entities.debt import Payment
from src.modules.debts.domain.errors import (
    DebtNotFoundError,
    InvalidDebtError,
    OverpaidError,
)
from src.modules.debts.domain.validation import ensure_note


@dataclass
class AddPaymentUseCase:
    """A partial repayment. Marks progress on the ledger; moves no balance.

    Overpaying is rejected, not clamped: a payment above what is owed is either a typo
    or a different agreement (a new debt the other way), and both deserve the user's
    attention rather than a silent `remaining: 0`.
    """

    debt_repository: DebtRepository

    async def execute(self, input_dto: AddPaymentInputDTO) -> DebtDTO:
        debt = await self.debt_repository.find(input_dto.user_id, input_dto.debt_id)
        if debt is None:
            raise DebtNotFoundError()

        if input_dto.amount <= 0:
            raise InvalidDebtError("A payment has to be a positive amount")
        if input_dto.amount > debt_status.remaining(debt):
            raise OverpaidError()

        updated = debt.with_payment(
            Payment.create(
                amount=input_dto.amount,
                paid_on=input_dto.today,
                note=ensure_note(input_dto.note),
            )
        )
        await self.debt_repository.save(updated)
        return DebtDTO.from_domain(updated, input_dto.today)
