from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID, uuid4

from src.modules.debts.domain.entities.counterparty import Counterparty, name_key
from src.modules.debts.domain.entities.debt import Debt, Direction, Payment
from src.modules.debts.domain.entities.shared_event import SharedEvent

T = TypeVar("T")

FIXED_NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=UTC)
TODAY = "2026-07-27"
CURRENCY = "COP"


class FakeDebtRepository:
    def __init__(self, debts: list[Debt] | None = None) -> None:
        self.debts = list(debts or [])

    async def list_by_user(self, user_id: UUID) -> list[Debt]:
        return [d for d in self.debts if d.user_id == user_id]

    async def list_by_event(self, user_id: UUID, event_id: str) -> list[Debt]:
        return [d for d in self.debts if d.user_id == user_id and d.event_id == event_id]

    async def find(self, user_id: UUID, debt_id: str) -> Debt | None:
        for debt in self.debts:
            if debt.id == debt_id and debt.user_id == user_id:
                return debt
        return None

    async def save(self, debt: Debt) -> None:
        for index, existing in enumerate(self.debts):
            if existing.id == debt.id:
                self.debts[index] = debt
                return
        self.debts.append(debt)

    async def delete(self, user_id: UUID, debt_id: str) -> None:
        self.debts = [d for d in self.debts if not (d.id == debt_id and d.user_id == user_id)]


class FakeCounterpartyRepository:
    """Dedupes by the normalized key, exactly like the unique index does."""

    def __init__(self, counterparties: list[Counterparty] | None = None) -> None:
        self.counterparties = list(counterparties or [])

    async def list_by_user(self, user_id: UUID) -> list[Counterparty]:
        return [c for c in self.counterparties if c.user_id == user_id]

    async def find(self, user_id: UUID, counterparty_id: str) -> Counterparty | None:
        for counterparty in self.counterparties:
            if counterparty.id == counterparty_id and counterparty.user_id == user_id:
                return counterparty
        return None

    async def find_by_name(self, user_id: UUID, name: str) -> Counterparty | None:
        key = name_key(name)
        for counterparty in self.counterparties:
            if counterparty.user_id == user_id and name_key(counterparty.name) == key:
                return counterparty
        return None

    async def save(self, counterparty: Counterparty) -> None:
        for index, existing in enumerate(self.counterparties):
            if existing.id == counterparty.id:
                self.counterparties[index] = counterparty
                return
        clash = [
            c
            for c in self.counterparties
            if c.user_id == counterparty.user_id and name_key(c.name) == name_key(counterparty.name)
        ]
        if clash:
            raise AssertionError("the unique index would have rejected this insert")
        self.counterparties.append(counterparty)


class FakeEventRepository:
    def __init__(self, events: list[SharedEvent] | None = None) -> None:
        self.events = list(events or [])

    async def list_by_user(self, user_id: UUID) -> list[SharedEvent]:
        return [e for e in self.events if e.user_id == user_id]

    async def find(self, user_id: UUID, event_id: str) -> SharedEvent | None:
        for event in self.events:
            if event.id == event_id and event.user_id == user_id:
                return event
        return None

    async def save(self, event: SharedEvent) -> None:
        for index, existing in enumerate(self.events):
            if existing.id == event.id:
                self.events[index] = event
                return
        self.events.append(event)

    async def delete(self, user_id: UUID, event_id: str) -> None:
        self.events = [e for e in self.events if not (e.id == event_id and e.user_id == user_id)]


class ImmediateUnitOfWork:
    """Runs the operation without a transaction — enough to assert the writes.

    Atomicity is a Mongo behaviour, verified end-to-end against docker.
    """

    def __init__(self) -> None:
        self.calls = 0

    async def atomic(self, operation: Callable[[], Awaitable[T]]) -> T:
        self.calls += 1
        return await operation()


def counterparty(*, user_id: UUID, name: str = "Juan Felipe") -> Counterparty:
    return Counterparty.create(user_id=user_id, name=name, created_at=FIXED_NOW)


def debt(
    *,
    user_id: UUID,
    direction: Direction = "incoming",
    counterparty_id: str = "juan",
    amount: int = 120_000,
    due_on: str | None = None,
    note: str | None = None,
    event_id: str | None = None,
    payments: tuple[Payment, ...] = (),
    created_at: datetime = FIXED_NOW,
) -> Debt:
    return Debt(
        id=str(uuid4()),
        user_id=user_id,
        direction=direction,
        counterparty_id=counterparty_id,
        amount=amount,
        currency=CURRENCY,
        due_on=due_on,
        note=note,
        event_id=event_id,
        payments=payments,
        created_at=created_at,
    )


def payment(*, amount: int, paid_on: str = TODAY, note: str | None = None) -> Payment:
    return Payment.create(amount=amount, paid_on=paid_on, note=note)


def new_user_id() -> UUID:
    return uuid4()
