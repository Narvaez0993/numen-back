from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.debts.application.dto.debt import DebtDTO
from src.modules.debts.application.dto.debt_commands import CreateDebtInputDTO
from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.debts.application.services.counterparty_resolver import (
    CounterpartyResolver,
)
from src.modules.debts.domain.entities.debt import Debt
from src.modules.debts.domain.validation import (
    ensure_amount,
    ensure_direction,
    ensure_due_on,
    ensure_note,
)


@dataclass
class CreateDebtUseCase:
    """A one-on-one debt. It records; it moves no money."""

    debt_repository: DebtRepository
    counterparty_resolver: CounterpartyResolver

    async def execute(self, input_dto: CreateDebtInputDTO) -> DebtDTO:
        direction = ensure_direction(input_dto.direction)
        amount = ensure_amount(input_dto.amount)
        due_on = ensure_due_on(input_dto.due_on)
        note = ensure_note(input_dto.note)

        counterparty = await self.counterparty_resolver.resolve(
            input_dto.user_id,
            counterparty_id=input_dto.counterparty_id,
            counterparty_name=input_dto.counterparty_name,
        )

        debt = Debt.create(
            user_id=input_dto.user_id,
            direction=direction,
            counterparty_id=counterparty.id,
            amount=amount,
            currency=input_dto.currency,
            due_on=due_on,
            note=note,
            event_id=None,
            created_at=datetime.now(UTC),
        )
        await self.debt_repository.save(debt)
        return DebtDTO.from_domain(debt, input_dto.today)
