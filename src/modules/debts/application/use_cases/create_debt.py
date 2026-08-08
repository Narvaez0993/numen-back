from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.debts.application.dto.debt import DebtDTO
from src.modules.debts.application.dto.debt_commands import CreateDebtInputDTO
from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.debts.application.ports.settlement_reader import NO_SETTLEMENT
from src.modules.debts.application.ports.transfer_recorder import TransferRecorder
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
from src.shared.application.ports.unit_of_work import UnitOfWork


@dataclass
class CreateDebtUseCase:
    """A one-on-one debt, and — when cash actually changed hands — the transfer
    that carried it.

    `account_id` is optional because not every debt moves money. Lending a friend
    $5.000 does: it leaves an account and becomes a claim, so it travels as a
    transfer and the month's expenses do not budge — you are not poorer for having
    lent. Splitting a dinner does not: the bill already left as one expense, and
    the debts that follow only record who owes what.

    Handing money over is never an expense. That arrives once, later, and only if
    the debt is written off.

    The debt and its transfer are written as ONE unit, because half of them is worse
    than neither: a debt whose loan never landed shows a friend owing money that
    never left the account. That is not hypothetical — a routing bug once made the
    transfer fail after the debt was already saved, and every retry left another
    phantom behind until the screen listed ten loans that had never happened.
    """

    debt_repository: DebtRepository
    counterparty_resolver: CounterpartyResolver
    transfer_recorder: TransferRecorder
    unit_of_work: UnitOfWork

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
        account_id = input_dto.account_id

        async def write() -> None:
            await self.debt_repository.save(debt)
            if account_id:
                await self.transfer_recorder.record(
                    user_id=input_dto.user_id,
                    currency=input_dto.currency,
                    description=note or _DESCRIPTION[direction],
                    amount=amount,
                    account_id=account_id,
                    debt_id=debt.id,
                    # `incoming` = they owe me, so the cash left my account to reach them.
                    direction="out" if direction == "incoming" else "in",
                    occurred_on=input_dto.today,
                )

        # `debt` is built above, outside the unit: a retried transaction re-runs this
        # body, and rebuilding it would mint a new id on every attempt.
        await self.unit_of_work.atomic(write)

        # Freshly created: nothing has been repaid yet, whatever moved just now was
        # the principal itself.
        return DebtDTO.from_domain(debt, NO_SETTLEMENT, input_dto.today)


#: A loan with no note still needs a name in Movimientos.
_DESCRIPTION: dict[str, str] = {
    "incoming": "Préstamo hecho",
    "outgoing": "Préstamo recibido",
}
