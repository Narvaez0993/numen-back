from dataclasses import dataclass
from uuid import UUID

from src.modules.debts.application.dto.debt import (
    CounterpartyDTO,
    DebtDTO,
    DebtsSnapshotDTO,
    DirectionTotalDTO,
    SharedEventDTO,
)
from src.modules.debts.application.dto.debt_commands import DebtsSnapshotInputDTO
from src.modules.debts.application.ports.counterparty_repository import (
    CounterpartyRepository,
)
from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.debts.application.ports.event_repository import EventRepository
from src.modules.debts.application.ports.settlement_reader import (
    NO_SETTLEMENT,
    DebtSettlement,
    SettlementReader,
)
from src.modules.debts.application.services import settlement as settlement_service
from src.modules.debts.domain import status as debt_status
from src.modules.debts.domain.entities.debt import Debt


@dataclass
class GetDebtsSnapshotUseCase:
    """The Deudas screen in one read: people, events, debts and the two totals.

    Totals count **live balances only** — a paid debt is history, not money between
    you. They are summed here with the same pure functions that fill each row, so the
    header and the list cannot disagree.
    """

    debt_repository: DebtRepository
    counterparty_repository: CounterpartyRepository
    event_repository: EventRepository
    settlement_reader: SettlementReader

    async def execute(self, input_dto: DebtsSnapshotInputDTO) -> DebtsSnapshotDTO:
        return await self.execute_for(input_dto.user_id, input_dto.currency, input_dto.today)

    async def execute_for(self, user_id: UUID, currency: str, today: str) -> DebtsSnapshotDTO:
        debts = await self.debt_repository.list_by_user(user_id)
        counterparties = await self.counterparty_repository.list_by_user(user_id)
        events = await self.event_repository.list_by_user(user_id)
        # One read for every debt's cash history: what came back is the transfers,
        # so the rows and the totals are both answered from the same source.
        settlements = await self.settlement_reader.settlements(user_id)

        # Newest first; ties broken by id so the order is stable across reads.
        debts.sort(key=lambda debt: (debt.created_at, debt.id), reverse=True)

        def settled(debt: Debt) -> DebtSettlement:
            return settlements.get(debt.id, NO_SETTLEMENT)

        return DebtsSnapshotDTO(
            currency=currency,
            today=today,
            i_owe=_direction_total(debts, settlements, "outgoing"),
            owed_to_me=_direction_total(debts, settlements, "incoming"),
            counterparties=[CounterpartyDTO.from_domain(c) for c in counterparties],
            events=[SharedEventDTO.from_domain(e) for e in events],
            debts=[DebtDTO.from_domain(debt, settled(debt), today) for debt in debts],
        )


def _direction_total(
    debts: list[Debt], settlements: dict[str, DebtSettlement], direction: str
) -> DirectionTotalDTO:
    alive = [
        left
        for debt in debts
        if debt.direction == direction
        and (
            left := debt_status.remaining(
                debt,
                settlement_service.repaid(debt, settlements.get(debt.id, NO_SETTLEMENT)),
            )
        )
        > 0
    ]
    return DirectionTotalDTO(total=sum(alive), count=len(alive))
