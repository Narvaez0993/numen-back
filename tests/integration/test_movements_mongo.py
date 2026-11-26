"""Movements against a real MongoDB: atomicity, the ledger, idempotency and listing speed.

These are the guarantees the unit tests cannot give: they use an `ImmediateUnitOfWork`
that runs the operation without a transaction, so "all or nothing" is only provable
against Mongo itself.
"""

import time
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from pymongo import AsyncMongoClient

from src.modules.accounts.adapters.outbound.persistence.repositories.mongo_account_repository import (  # noqa: E501
    MongoAccountRepository,
)
from src.modules.accounts.adapters.outbound.persistence.repositories.mongo_credit_card_repository import (  # noqa: E501
    MongoCreditCardRepository,
)
from src.modules.movements.adapters.outbound.ledger.accounts_source_ledger import (
    AccountsSourceLedger,
)
from src.modules.movements.adapters.outbound.persistence.repositories.mongo_idempotency_store import (  # noqa: E501
    MongoIdempotencyStore,
)
from src.modules.movements.adapters.outbound.persistence.repositories.mongo_movement_repository import (  # noqa: E501
    MongoMovementRepository,
)
from src.modules.movements.application.dto.list_movements import ListMovementsInputDTO
from src.modules.movements.application.ports.movement_repository import MovementQuery
from src.modules.movements.application.ports.source_ledger import SourceSnapshot
from src.modules.movements.application.services.movement_references import (
    MovementReferences,
)
from src.modules.movements.application.use_cases.create_movement import CreateMovementUseCase
from src.modules.movements.application.use_cases.list_movements import ListMovementsUseCase
from src.modules.movements.domain.entities.movement import Movement, SourceRef
from src.shared.adapters.outbound.persistence.mongo_unit_of_work import MongoUnitOfWork
from tests.unit.accounts.fakes import make_account, make_card
from tests.unit.movements.fakes import FIXED_NOW, TODAY, FakeCategoryLookup, FixedClock
from tests.unit.movements.helpers import create_input


class ExplodingLedger:
    """Delegates to the real ledger and raises on the Nth `apply_delta`.

    The Nth call raises *after* the previous ones already wrote inside the transaction,
    which is exactly the "fails halfway" case atomicity is for.
    """

    def __init__(self, inner: AccountsSourceLedger, *, fail_on_call: int) -> None:
        self._inner = inner
        self._fail_on_call = fail_on_call
        self.calls = 0

    async def find(self, user_id: UUID, ref: SourceRef) -> SourceSnapshot | None:
        return await self._inner.find(user_id, ref)

    async def apply_delta(self, user_id: UUID, ref: SourceRef, delta: int) -> None:
        self.calls += 1
        if self.calls == self._fail_on_call:
            raise RuntimeError("the ledger failed halfway")
        await self._inner.apply_delta(user_id, ref, delta)


class Stack:
    """The real adapters wired the way the composition root wires them."""

    def __init__(self, client: AsyncMongoClient[Any]) -> None:
        self.accounts = MongoAccountRepository()
        self.cards = MongoCreditCardRepository()
        self.movements = MongoMovementRepository()
        self.idempotency = MongoIdempotencyStore()
        self.ledger = AccountsSourceLedger(
            account_repository=self.accounts, credit_card_repository=self.cards
        )
        self.unit_of_work = MongoUnitOfWork(client)

    def creator(self, ledger: Any = None) -> CreateMovementUseCase:
        ledger = ledger or self.ledger
        return CreateMovementUseCase(
            movement_repository=self.movements,
            source_ledger=ledger,
            references=MovementReferences(
                source_ledger=ledger, category_lookup=FakeCategoryLookup()
            ),
            idempotency_store=self.idempotency,
            unit_of_work=self.unit_of_work,
            clock=FixedClock(),
        )

    async def balance(self, user_id: UUID, account_id: str) -> int:
        account = await self.accounts.find(user_id, account_id)
        assert account is not None
        return account.balance

    async def debt(self, user_id: UUID, card_id: str) -> int:
        card = await self.cards.find(user_id, card_id)
        assert card is not None
        return card.debt

    async def stored(self, user_id: UUID) -> list[Movement]:
        return await self.movements.search(MovementQuery(user_id=user_id, limit=1000))


@pytest.fixture
def stack(mongo_client: AsyncMongoClient[Any]) -> Stack:
    return Stack(mongo_client)


async def seed(stack: Stack, user_id: UUID, *, balance: int = 1_000_000, debt: int = 0):
    nequi = make_account(user_id, name="Nequi", balance=balance)
    banco = make_account(user_id, name="Banco", balance=200_000)
    visa = make_card(user_id, name="Visa", debt=debt)
    for entity in (nequi, banco):
        await stack.accounts.save(entity)
    await stack.cards.save(visa)
    return nequi, banco, visa


@pytest.mark.asyncio
async def test_hu15_a_transfer_that_fails_on_the_destination_leaves_no_trace(stack: Stack) -> None:
    """HU-15 · «La transferencia es atómica»: falla la aplicación sobre el destino,
    el origen conserva su saldo y no queda movimiento guardado."""
    user_id = uuid4()
    nequi, banco, _ = await seed(stack, user_id)
    # deltas of a transfer: source first, destination second -> fail on the 2nd.
    ledger = ExplodingLedger(stack.ledger, fail_on_call=2)

    with pytest.raises(RuntimeError, match="halfway"):
        await stack.creator(ledger).execute(
            create_input(
                user_id,
                type="transfer",
                amount=300_000,
                source_id=nequi.id,
                destination_type="account",
                destination_id=banco.id,
                category_id=None,
            )
        )

    assert ledger.calls == 2  # the source WAS written inside the transaction...
    assert await stack.balance(user_id, nequi.id) == 1_000_000  # ...and rolled back
    assert await stack.balance(user_id, banco.id) == 200_000
    assert await stack.stored(user_id) == []


@pytest.mark.asyncio
async def test_hu16_a_card_purchase_that_fails_after_saving_changes_nothing(stack: Stack) -> None:
    """HU-16 · «La operación es atómica»: si falla la actualización de la deuda, el
    movimiento no queda guardado y la deuda no cambia."""
    user_id = uuid4()
    _, _, visa = await seed(stack, user_id, debt=100_000)
    ledger = ExplodingLedger(stack.ledger, fail_on_call=1)

    with pytest.raises(RuntimeError, match="halfway"):
        await stack.creator(ledger).execute(
            create_input(
                user_id,
                type="expense",
                amount=300_000,
                source_type="credit_card",
                source_id=visa.id,
            )
        )

    assert await stack.debt(user_id, visa.id) == 100_000
    assert await stack.stored(user_id) == []


@pytest.mark.asyncio
async def test_the_ledger_moves_balances_and_debts_for_real(stack: Stack) -> None:
    """An expense lowers an account and raises a card's debt; paying the card (a
    transfer account -> card) lowers both."""
    user_id = uuid4()
    nequi, _, visa = await seed(stack, user_id, balance=1_000_000, debt=0)
    creator = stack.creator()

    await creator.execute(create_input(user_id, amount=50_000, source_id=nequi.id))
    assert await stack.balance(user_id, nequi.id) == 950_000

    await creator.execute(
        create_input(user_id, amount=400_000, source_type="credit_card", source_id=visa.id)
    )
    assert await stack.debt(user_id, visa.id) == 400_000
    assert await stack.balance(user_id, nequi.id) == 950_000  # cash did not move

    await creator.execute(
        create_input(
            user_id,
            type="transfer",
            amount=150_000,
            source_id=nequi.id,
            destination_type="credit_card",
            destination_id=visa.id,
            category_id=None,
        )
    )
    assert await stack.balance(user_id, nequi.id) == 800_000
    assert await stack.debt(user_id, visa.id) == 250_000


@pytest.mark.asyncio
async def test_the_same_idempotency_key_twice_leaves_one_movement(stack: Stack) -> None:
    user_id = uuid4()
    nequi, _, _ = await seed(stack, user_id)
    creator = stack.creator()
    payload = create_input(user_id, amount=20_000, source_id=nequi.id, idempotency_key="key-123")

    first = await creator.execute(payload)
    second = await creator.execute(payload)

    assert second.id == first.id
    assert len(await stack.stored(user_id)) == 1
    assert await stack.balance(user_id, nequi.id) == 980_000  # charged once


@pytest.mark.asyncio
async def test_hu23_a_month_of_a_thousand_movements_lists_in_under_two_seconds(
    stack: Stack,
) -> None:
    """HU-23 · «Rendimiento del listado»: mil movimientos, el listado del mes completo
    se presenta en menos de dos segundos y trae los mil."""
    user_id = uuid4()
    nequi, _, _ = await seed(stack, user_id)
    for i in range(1000):
        await stack.movements.save(
            Movement(
                id=f"perf-{i:04d}",
                user_id=user_id,
                type="expense",
                description=f"Gasto {i}",
                amount=1_000 + i,
                currency="COP",
                source=SourceRef(type="account", id=nequi.id),
                destination=None,
                category_id="cafe",
                occurred_on=f"{TODAY[:8]}{(i % 25) + 1:02d}",
                captured_via="manual",
                created_at=FIXED_NOW + timedelta(seconds=i),
            )
        )
    use_case = ListMovementsUseCase(movement_repository=stack.movements)
    query = ListMovementsInputDTO(
        user_id=user_id, date_from="2026-07-01", date_to="2026-07-31", limit=1000
    )

    started = time.perf_counter()
    output = await use_case.execute(query)
    elapsed = time.perf_counter() - started

    print(f"\nHU-23 listing of 1000 movements: {elapsed * 1000:.0f} ms")
    assert len(output.movements) == 1000
    assert elapsed < 2.0
