from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from src.modules.debts.application.ports.settlement_reader import (
    DebtMovement,
    DebtSettlement,
)
from src.modules.movements.application.dto.debt_transfers import DebtTransfersInputDTO
from src.modules.movements.application.use_cases.get_debt_transfers import (
    GetDebtTransfersUseCase,
)


@dataclass
class MovementsSettlementReader:
    """`SettlementReader` backed by the movements module.

    Talks to its use case, never to its collection: the transfers live with the rows
    that make them up, and this is only the translation into what a debt needs.
    """

    get_debt_transfers: GetDebtTransfersUseCase

    async def settlements(self, user_id: UUID) -> dict[str, DebtSettlement]:
        output = await self.get_debt_transfers.execute(DebtTransfersInputDTO(user_id=user_id))

        inbound: dict[str, list[DebtMovement]] = defaultdict(list)
        outbound: dict[str, list[DebtMovement]] = defaultdict(list)
        for row in output.transfers:
            side = inbound if row.into_debt else outbound
            side[row.debt_id].append(
                DebtMovement(
                    movement_id=row.movement_id,
                    amount=row.amount,
                    occurred_on=row.occurred_on,
                    description=row.description,
                    # The one movement out of a debt that is not a repayment.
                    is_loss=row.movement_type == "expense",
                )
            )

        return {
            debt_id: DebtSettlement(
                debt_id=debt_id,
                into_debt=tuple(inbound.get(debt_id, ())),
                out_of_debt=tuple(outbound.get(debt_id, ())),
            )
            for debt_id in inbound.keys() | outbound.keys()
        }
