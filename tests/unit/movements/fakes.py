from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID, uuid4

from src.modules.movements.application.ports.idempotency_store import (
    IdempotencyConflictError,
)
from src.modules.movements.application.ports.movement_repository import MovementQuery
from src.modules.movements.application.ports.source_ledger import SourceSnapshot
from src.modules.movements.domain.entities.movement import Movement, SourceRef

FIXED_NOW = datetime(2026, 7, 25, 12, 0, 0, tzinfo=UTC)
TODAY = "2026-07-25"
CURRENCY = "COP"

T = TypeVar("T")


class FixedClock:
    def now(self) -> datetime:
        return FIXED_NOW


class ImmediateUnitOfWork:
    """Runs the operation without a transaction — enough to assert the writes.

    Atomicity itself is a Mongo behavior, verified end-to-end against docker.
    """

    def __init__(self) -> None:
        self.calls = 0

    async def atomic(self, operation: Callable[[], Awaitable[T]]) -> T:
        self.calls += 1
        return await operation()


class InMemoryMovementRepository:
    def __init__(self, *movements: Movement) -> None:
        self.movements: list[Movement] = list(movements)

    async def list(self, query: MovementQuery) -> list[Movement]:
        found = [m for m in self.movements if m.user_id == query.user_id]
        if query.date_from is not None:
            found = [m for m in found if m.occurred_on >= query.date_from]
        if query.date_to is not None:
            found = [m for m in found if m.occurred_on <= query.date_to]
        if query.type is not None:
            found = [m for m in found if m.type == query.type]
        if query.category_id is not None:
            found = [m for m in found if m.category_id == query.category_id]
        if query.source_id is not None:
            found = [
                m
                for m in found
                if m.source.id == query.source_id
                or (m.destination is not None and m.destination.id == query.source_id)
            ]
        found.sort(key=lambda m: (m.occurred_on, m.created_at), reverse=True)
        return found[: query.limit]

    async def find(self, user_id: UUID, movement_id: str) -> Movement | None:
        return next(
            (m for m in self.movements if m.id == movement_id and m.user_id == user_id),
            None,
        )

    async def save(self, movement: Movement) -> None:
        self.movements = [m for m in self.movements if m.id != movement.id]
        self.movements.append(movement)

    async def delete(self, user_id: UUID, movement_id: str) -> None:
        self.movements = [
            m for m in self.movements if not (m.id == movement_id and m.user_id == user_id)
        ]


class FakeSourceLedger:
    """Tracks positions per source so tests can assert the cash-basis outcome.

    Mirrors the real adapter's translation: an account moves by the delta, a card
    moves by its opposite (less debt when your position improves).
    """

    def __init__(
        self, *, accounts: dict[str, int] | None = None, cards: dict[str, int] | None = None
    ) -> None:
        self.accounts: dict[str, int] = dict(accounts or {})
        self.cards: dict[str, int] = dict(cards or {})
        self.currency = CURRENCY

    async def find(self, user_id: UUID, ref: SourceRef) -> SourceSnapshot | None:
        pool = self.accounts if ref.type == "account" else self.cards
        if ref.id not in pool:
            return None
        return SourceSnapshot(ref=ref, type=ref.type, currency=self.currency)

    async def apply_delta(self, user_id: UUID, ref: SourceRef, delta: int) -> None:
        if ref.type == "account":
            self.accounts[ref.id] += delta
        else:
            self.cards[ref.id] -= delta


class FakeCategoryLookup:
    def __init__(self, *, expense: set[str] | None = None, income: set[str] | None = None) -> None:
        self.expense = expense or {"mercado", "cafe"}
        self.income = income or {"salario"}

    async def exists(self, user_id: UUID, category_id: str, flow: str) -> bool:
        pool = self.income if flow == "income" else self.expense
        return category_id in pool


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self.keys: dict[tuple[str, str], str] = {}

    async def find(self, user_id: UUID, key: str) -> str | None:
        return self.keys.get((str(user_id), key))

    async def reserve(self, user_id: UUID, key: str, movement_id: str) -> None:
        slot = (str(user_id), key)
        if slot in self.keys:
            raise IdempotencyConflictError(key)
        self.keys[slot] = movement_id


def new_user_id() -> UUID:
    return uuid4()
