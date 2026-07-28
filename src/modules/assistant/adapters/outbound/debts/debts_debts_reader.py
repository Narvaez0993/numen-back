from dataclasses import dataclass
from uuid import UUID

from src.modules.assistant.application.ports.debts_reader import DebtsView, DebtView
from src.modules.debts.application.use_cases.get_debts_snapshot import GetDebtsSnapshotUseCase


@dataclass
class DebtsDebtsReader:
    """`DebtsReader` backed by debts. Counterparty ids become names here — the
    model reasons about "Andrés", not about UUIDs."""

    get_debts_snapshot: GetDebtsSnapshotUseCase

    async def snapshot(self, user_id: UUID, currency: str, today: str) -> DebtsView:
        output = await self.get_debts_snapshot.execute_for(user_id, currency, today)
        names = {c.id: c.name for c in output.counterparties}
        return DebtsView(
            i_owe_total=output.i_owe.total,
            owed_to_me_total=output.owed_to_me.total,
            debts=tuple(
                DebtView(
                    id=d.id,
                    direction=d.direction,
                    counterparty=names.get(d.counterparty_id, "?"),
                    amount=d.amount,
                    paid_total=d.paid_total,
                    remaining=d.remaining,
                    status=d.status,
                    due_on=d.due_on,
                )
                for d in output.debts
            ),
        )
