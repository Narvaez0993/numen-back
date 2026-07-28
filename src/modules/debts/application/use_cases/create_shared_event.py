from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.debts.application.dto.debt import DebtsSnapshotDTO
from src.modules.debts.application.dto.debt_commands import CreateSharedEventInputDTO
from src.modules.debts.application.ports.counterparty_repository import (
    CounterpartyRepository,
)
from src.modules.debts.application.ports.debt_repository import DebtRepository
from src.modules.debts.application.ports.event_repository import EventRepository
from src.modules.debts.application.services.counterparty_resolver import (
    CounterpartyResolver,
)
from src.modules.debts.application.use_cases.get_debts_snapshot import (
    GetDebtsSnapshotUseCase,
)
from src.modules.debts.domain.entities.debt import Debt
from src.modules.debts.domain.entities.shared_event import (
    MAX_EVENT_NAME_LENGTH,
    SharedEvent,
)
from src.modules.debts.domain.errors import InvalidDebtError
from src.modules.debts.domain.validation import (
    ensure_amount,
    ensure_direction,
    ensure_due_on,
)
from src.shared.application.ports.unit_of_work import UnitOfWork

# Enough for any dinner table; a guard against a runaway client, not a product rule.
MAX_SPLITS = 30


@dataclass
class CreateSharedEventUseCase:
    """The dinner, split: one event plus a debt per person, written atomically.

    The split happens **here, once** — the event stores no formula, and the debts it
    produces are plain debts from then on. The user's own share is whatever the splits
    leave of the total; it is not a debt, so it is never stored anywhere.

    Everything lands in one transaction: resolving people first (outside it — creating
    a counterparty is idempotent by the name key), then event + debts inside, so a
    half-created dinner cannot exist.
    """

    debt_repository: DebtRepository
    event_repository: EventRepository
    counterparty_repository: CounterpartyRepository
    counterparty_resolver: CounterpartyResolver
    unit_of_work: UnitOfWork
    snapshot: GetDebtsSnapshotUseCase

    async def execute(self, input_dto: CreateSharedEventInputDTO) -> DebtsSnapshotDTO:
        direction = ensure_direction(input_dto.direction)
        total = ensure_amount(input_dto.total)
        due_on = ensure_due_on(input_dto.due_on)
        name = " ".join(input_dto.name.split())
        if not name or len(name) > MAX_EVENT_NAME_LENGTH:
            raise InvalidDebtError(f"Event name must be 1-{MAX_EVENT_NAME_LENGTH} characters")

        if not 2 <= len(input_dto.splits) <= MAX_SPLITS:
            raise InvalidDebtError("A shared event needs from 2 to 30 people")
        if any(split.amount <= 0 for split in input_dto.splits):
            raise InvalidDebtError("Every share has to be a positive amount")
        if sum(split.amount for split in input_dto.splits) > total:
            raise InvalidDebtError("The shares add up to more than the total")

        # People first, outside the transaction: resolving by name is idempotent (the
        # unique key dedupes), so a retry cannot mint twins.
        people = [
            await self.counterparty_resolver.resolve(
                input_dto.user_id,
                counterparty_id=split.counterparty_id,
                counterparty_name=split.counterparty_name,
            )
            for split in input_dto.splits
        ]
        if len({person.id for person in people}) != len(people):
            raise InvalidDebtError("The same person appears twice in the split")

        now = datetime.now(UTC)
        event = SharedEvent.create(
            user_id=input_dto.user_id,
            name=name,
            total=total,
            occurred_on=input_dto.today,
            created_at=now,
        )
        debts = [
            Debt.create(
                user_id=input_dto.user_id,
                direction=direction,
                counterparty_id=person.id,
                amount=split.amount,
                currency=input_dto.currency,
                due_on=due_on,
                note=None,
                event_id=event.id,
                created_at=now,
            )
            for person, split in zip(people, input_dto.splits, strict=True)
        ]

        async def write() -> None:
            await self.event_repository.save(event)
            for debt in debts:
                await self.debt_repository.save(debt)

        await self.unit_of_work.atomic(write)

        # The screen redraws the whole list after a split; one read spares it a second
        # round trip and reuses the exact same derivations.
        return await self.snapshot.execute_for(
            input_dto.user_id, input_dto.currency, input_dto.today
        )
