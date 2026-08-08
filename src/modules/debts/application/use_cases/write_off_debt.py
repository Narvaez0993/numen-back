from dataclasses import dataclass

from src.modules.debts.application.dto.debt import DebtDTO
from src.modules.debts.application.dto.debt_commands import WriteOffDebtInputDTO
from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.debts.application.ports.settlement_reader import (
    NO_SETTLEMENT,
    SettlementReader,
)
from src.modules.debts.application.ports.transfer_recorder import TransferRecorder
from src.modules.debts.application.services import settlement as settlement_service
from src.modules.debts.domain.errors import (
    AlreadyWrittenOffError,
    DebtNotFoundError,
    NotWritableOffError,
)


@dataclass
class WriteOffDebtUseCase:
    """Giving up on a claim — the one moment lending becomes spending.

    Everything before this was a transfer: the cash left the account and became a
    claim, and the user was no poorer for it. Here the claim dies, so the loss lands
    now, in this month, as an **expense out of the debt**. Not out of an account —
    that one was already debited the day the money was lent, and charging it again
    would say the user paid twice for the same friend.

    Two things it deliberately does not do:

    **It never writes off what it never lent.** A dinner split owes real money and
    moved none: the bill already left as one expense. Booking a second one would
    charge the user twice for the same meal, so the expense covers only the cash that
    actually crossed and has not come back — often zero, and then the debt simply
    closes with no movement at all.

    **It only applies to money owed TO the user.** You write off a claim, not a
    liability. Being forgiven a debt you owe is not a loss, it is a windfall, and it
    is a different story with different arithmetic — one this app does not tell yet
    rather than tells wrong.
    """

    debt_repository: DebtRepository
    settlement_reader: SettlementReader
    transfer_recorder: TransferRecorder

    async def execute(self, input_dto: WriteOffDebtInputDTO) -> DebtDTO:
        debt = await self.debt_repository.find(input_dto.user_id, input_dto.debt_id)
        if debt is None:
            raise DebtNotFoundError()
        if debt.direction != "incoming":
            raise NotWritableOffError()
        if debt.written_off_on is not None:
            raise AlreadyWrittenOffError()

        settlements = await self.settlement_reader.settlements(input_dto.user_id)
        before = settlements.get(debt.id, NO_SETTLEMENT)
        # The cash that left and has not come back. Everything else was never money
        # in flight: it was a share of a bill that already hit the month.
        lost = settlement_service.principal(debt, before) - settlement_service.repaid(debt, before)

        if lost > 0:
            await self.transfer_recorder.record_loss(
                user_id=input_dto.user_id,
                currency=debt.currency,
                description=_DESCRIPTION,
                amount=lost,
                debt_id=debt.id,
                occurred_on=input_dto.today,
            )

        given_up = debt.with_changes(written_off_on=input_dto.today)
        await self.debt_repository.save(given_up)

        after = await self.settlement_reader.settlements(input_dto.user_id)
        return DebtDTO.from_domain(given_up, after.get(debt.id, NO_SETTLEMENT), input_dto.today)


#: What the loss is called in Movimientos. Plain on purpose — the user will meet this
#: row months later, in a list of groceries and rent, and it has to explain itself.
_DESCRIPTION = "Deuda dada por perdida"
