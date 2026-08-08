from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID, uuid4

from src.modules.debts.application.ports.settlement_reader import (
    DebtMovement,
    DebtSettlement,
)
from src.modules.debts.application.ports.transfer_recorder import RecordedTransfer
from src.modules.debts.domain.entities.counterparty import Counterparty, name_key
from src.modules.debts.domain.entities.debt import Debt, Direction
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

    Atomicity is a Mongo behaviour, verified end-to-end against docker. What CAN be
    asserted here is that the writes were handed over as one unit at all, which is
    the part a refactor drops by accident.
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
    written_off_on: str | None = None,
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
        written_off_on=written_off_on,
        created_at=created_at,
    )


def settled(
    debt: Debt,
    *,
    instalments: tuple[int, ...] = (),
    principal: int | None = None,
) -> DebtSettlement:
    """A debt's cash history, built the way movements would report it.

    `instalments` are the payments that came back; `principal` is the cash handed over
    at the start, when there was any (a dinner split moves none). Which side each one
    lands on depends on the direction — an instalment on an `incoming` debt is money
    arriving in my account, and on an `outgoing` one it is money leaving.
    """
    paying_in = debt.direction == "incoming"
    paid = tuple(
        DebtMovement(
            movement_id=f"mov-{index}",
            amount=amount,
            occurred_on=TODAY,
            description="Abono",
        )
        for index, amount in enumerate(instalments)
    )
    lent = (
        ()
        if principal is None
        else (
            DebtMovement(
                movement_id="mov-principal",
                amount=principal,
                occurred_on=TODAY,
                description="Préstamo",
            ),
        )
    )
    return DebtSettlement(
        debt_id=debt.id,
        into_debt=lent if paying_in else paid,
        out_of_debt=paid if paying_in else lent,
    )


class FakeDebtLedger:
    """Stands in for movements: records the transfers AND answers what they add up to.

    One object for both ports on purpose. In production they are two adapters over the
    same collection, and a test double that let them disagree would hide the very bug
    the design exists to prevent — a repayment that outlives the movement that made it.

    Reverting drops the movement from the answer, seeded or recorded, because that is
    the whole claim the design makes: deleting the movement undoes the money AND the
    progress, with no second copy left telling a different story.
    """

    def __init__(self) -> None:
        self.recorded: list[dict[str, object]] = []
        self.reverted: list[str] = []
        self._seeded: dict[str, DebtSettlement] = {}

    def seed(self, settlement: DebtSettlement) -> None:
        """Cash that crossed before this test started."""
        self._seeded[settlement.debt_id] = settlement

    async def record(self, **kwargs: object) -> RecordedTransfer:
        movement_id = f"mov-{len(self.recorded) + 1}"
        self.recorded.append({**kwargs, "movement_id": movement_id, "is_loss": False})
        return RecordedTransfer(movement_id=movement_id)

    async def record_loss(self, **kwargs: object) -> RecordedTransfer:
        """The write-off. It leaves the debt like a repayment and means the opposite,
        so it lands on the same side flagged `is_loss` — exactly how the real reader
        reports an expense whose source is the debt."""
        movement_id = f"loss-{len(self.recorded) + 1}"
        self.recorded.append(
            {**kwargs, "movement_id": movement_id, "direction": "in", "is_loss": True}
        )
        return RecordedTransfer(movement_id=movement_id)

    async def revert(self, *, user_id: UUID, movement_id: str) -> bool:
        self.reverted.append(movement_id)
        return True

    async def settlements(self, user_id: UUID) -> dict[str, DebtSettlement]:
        result: dict[str, DebtSettlement] = {
            debt_id: _without(seeded, self.reverted) for debt_id, seeded in self._seeded.items()
        }
        for entry in self.recorded:
            if entry["movement_id"] in self.reverted:
                continue
            debt_id = str(entry["debt_id"])
            current = result.get(
                debt_id, DebtSettlement(debt_id=debt_id, into_debt=(), out_of_debt=())
            )
            moved = DebtMovement(
                movement_id=str(entry["movement_id"]),
                amount=int(entry["amount"]),  # type: ignore[arg-type]
                occurred_on=str(entry["occurred_on"]),
                description=str(entry["description"]),
                is_loss=bool(entry["is_loss"]),
            )
            result[debt_id] = (
                DebtSettlement(
                    debt_id=debt_id,
                    into_debt=(*current.into_debt, moved),
                    out_of_debt=current.out_of_debt,
                )
                if entry["direction"] == "out"
                else DebtSettlement(
                    debt_id=debt_id,
                    into_debt=current.into_debt,
                    out_of_debt=(*current.out_of_debt, moved),
                )
            )
        return result


def _without(settlement: DebtSettlement, reverted: list[str]) -> DebtSettlement:
    return DebtSettlement(
        debt_id=settlement.debt_id,
        into_debt=tuple(m for m in settlement.into_debt if m.movement_id not in reverted),
        out_of_debt=tuple(m for m in settlement.out_of_debt if m.movement_id not in reverted),
    )


def new_user_id() -> UUID:
    return uuid4()


class RollingBackUnitOfWork:
    """Undoes the repository's writes when the operation raises.

    `ImmediateUnitOfWork` is enough to assert that writes were handed over as one
    unit; this one models what Mongo actually does with them, which is the property
    a phantom debt violates. Kept as a separate double so the cheap one stays cheap.
    """

    def __init__(self, debts: "FakeDebtRepository") -> None:
        self.debts = debts
        self.calls = 0

    async def atomic(self, operation: Callable[[], Awaitable[T]]) -> T:
        self.calls += 1
        snapshot = list(self.debts.debts)
        try:
            return await operation()
        except Exception:
            self.debts.debts = snapshot
            raise


class FailingLedger(FakeDebtLedger):
    """A ledger whose transfer always fails — the shipped bug, in a test double.

    A routing bug made exactly this happen: the transfer blew up AFTER the debt was
    already saved, so every retry left another phantom loan behind.
    """

    async def record(self, **kwargs: object) -> RecordedTransfer:
        raise RuntimeError("the ledger refused this transfer")
