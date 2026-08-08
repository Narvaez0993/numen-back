from dataclasses import dataclass
from uuid import UUID

from src.modules.assistant.application.ports.debt_payment_recorder import RecordedPayment
from src.modules.debts.application.dto.debt_commands import AddPaymentInputDTO
from src.modules.debts.application.use_cases.add_payment import AddPaymentUseCase


@dataclass
class DebtsDebtPaymentRecorder:
    """`DebtPaymentRecorder` backed by debts — the same door the Deudas screen uses.

    Which means an abono captured by voice inherits everything the manual one has:
    the overpaid check, the transfer that really moves the account's balance, and the
    progress derived from that transfer rather than stored beside it.
    """

    add_payment: AddPaymentUseCase

    async def record(
        self,
        *,
        user_id: UUID,
        today: str,
        debt_id: str,
        amount: int,
        account_id: str,
        note: str | None,
    ) -> RecordedPayment:
        output = await self.add_payment.execute(
            AddPaymentInputDTO(
                user_id=user_id,
                debt_id=debt_id,
                today=today,
                amount=amount,
                account_id=account_id,
                note=note,
            )
        )
        return RecordedPayment(movement_id=output.movement_id)
