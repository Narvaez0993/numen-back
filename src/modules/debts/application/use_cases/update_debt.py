from dataclasses import dataclass

from src.modules.debts.application.dto.debt import DebtDTO
from src.modules.debts.application.dto.debt_commands import UpdateDebtInputDTO
from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.debts.domain import status as debt_status
from src.modules.debts.domain.entities.debt import Debt
from src.modules.debts.domain.errors import DebtNotFoundError, InvalidDebtError
from src.modules.debts.domain.validation import ensure_amount, ensure_due_on, ensure_note


@dataclass
class UpdateDebtUseCase:
    """Patches what a debt says, never who it is between.

    The person and the direction are identity — "now María owes me instead" is a new
    debt, not an edit. The amount can move, but never below what was already paid:
    the ledger cannot claim someone repaid more than the whole.
    """

    debt_repository: DebtRepository

    async def execute(self, input_dto: UpdateDebtInputDTO) -> DebtDTO:
        debt = await self.debt_repository.find(input_dto.user_id, input_dto.debt_id)
        if debt is None:
            raise DebtNotFoundError()

        updated = self._patched(debt, input_dto)
        await self.debt_repository.save(updated)
        return DebtDTO.from_domain(updated, input_dto.today)

    @staticmethod
    def _patched(debt: Debt, input_dto: UpdateDebtInputDTO) -> Debt:
        changes: dict[str, object] = {}
        if input_dto.amount is not None:
            amount = ensure_amount(input_dto.amount)
            if amount < debt_status.paid_total(debt):
                raise InvalidDebtError("The amount cannot be below what was already paid")
            changes["amount"] = amount
        if input_dto.clear_due_on:
            changes["due_on"] = None
        elif input_dto.due_on is not None:
            changes["due_on"] = ensure_due_on(input_dto.due_on)
        if input_dto.clear_note:
            changes["note"] = None
        elif input_dto.note is not None:
            changes["note"] = ensure_note(input_dto.note)
        return debt.with_changes(**changes) if changes else debt
