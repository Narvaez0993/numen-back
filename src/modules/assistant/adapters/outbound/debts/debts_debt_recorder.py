from dataclasses import dataclass
from uuid import UUID

from src.modules.assistant.application.ports.debt_recorder import RecordedDebt
from src.modules.debts.application.dto.debt_commands import CreateDebtInputDTO
from src.modules.debts.application.use_cases.create_debt import CreateDebtUseCase


@dataclass
class DebtsDebtRecorder:
    """`DebtRecorder` backed by debts — the same door the manual flow uses.

    Which means a debt captured by voice is a debt in every way that matters: the
    person is resolved (or created inline) once, the loan leaves the account as a
    real transfer, and what has been repaid stays derived from those movements.
    """

    create_debt: CreateDebtUseCase

    async def record(
        self,
        *,
        user_id: UUID,
        currency: str,
        today: str,
        direction: str,
        counterparty_id: str | None,
        counterparty_name: str | None,
        amount: int,
        account_id: str | None,
        due_on: str | None,
        note: str | None,
    ) -> RecordedDebt:
        output = await self.create_debt.execute(
            CreateDebtInputDTO(
                user_id=user_id,
                currency=currency,
                today=today,
                direction=direction,
                counterparty_id=counterparty_id,
                counterparty_name=counterparty_name,
                amount=amount,
                account_id=account_id,
                due_on=due_on,
                note=note,
            )
        )
        return RecordedDebt(debt_id=output.id)
