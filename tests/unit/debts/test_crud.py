"""Creating, patching, paying and deleting — and the people created on the way.

The parallel-ledger rule is invisible here by design: no fake ledger, no fake balance,
because the module never touches one. What is asserted instead is the arithmetic it
owns: payments cannot exceed what is owed, and the amount cannot sink below what was
already paid.
"""

import pytest

from src.modules.debts.application.dto.debt_commands import (
    AddPaymentInputDTO,
    CreateDebtInputDTO,
    DeleteDebtInputDTO,
    RemovePaymentInputDTO,
    UpdateDebtInputDTO,
)
from src.modules.debts.application.services.counterparty_resolver import (
    CounterpartyResolver,
)
from src.modules.debts.application.use_cases.add_payment import AddPaymentUseCase
from src.modules.debts.application.use_cases.create_debt import CreateDebtUseCase
from src.modules.debts.application.use_cases.delete_debt import DeleteDebtUseCase
from src.modules.debts.application.use_cases.remove_payment import RemovePaymentUseCase
from src.modules.debts.application.use_cases.update_debt import UpdateDebtUseCase
from src.modules.debts.domain.errors import (
    CounterpartyNotFoundError,
    DebtNotFoundError,
    InvalidDebtError,
    OverpaidError,
)

from .fakes import (
    CURRENCY,
    TODAY,
    FakeCounterpartyRepository,
    FakeDebtRepository,
    FakeEventRepository,
    counterparty,
    debt,
    new_user_id,
    payment,
)


def creator(
    debts: FakeDebtRepository,
    people: FakeCounterpartyRepository,
) -> CreateDebtUseCase:
    return CreateDebtUseCase(
        debt_repository=debts,
        counterparty_resolver=CounterpartyResolver(counterparty_repository=people),
    )


async def create(
    use_case: CreateDebtUseCase,
    *,
    user_id,
    direction: str = "incoming",
    counterparty_id: str | None = None,
    counterparty_name: str | None = None,
    amount: int = 120_000,
    due_on: str | None = None,
    note: str | None = None,
):
    return await use_case.execute(
        CreateDebtInputDTO(
            user_id=user_id,
            currency=CURRENCY,
            today=TODAY,
            direction=direction,
            counterparty_id=counterparty_id,
            counterparty_name=counterparty_name,
            amount=amount,
            due_on=due_on,
            note=note,
        )
    )


@pytest.mark.asyncio
async def test_a_new_name_creates_the_person_inline() -> None:
    user_id = new_user_id()
    people = FakeCounterpartyRepository()

    output = await create(
        creator(FakeDebtRepository(), people), user_id=user_id, counterparty_name="Juan Felipe"
    )

    created = await people.list_by_user(user_id)
    assert len(created) == 1
    assert created[0].name == "Juan Felipe"
    assert output.counterparty_id == created[0].id
    assert output.status == "pending"
    assert output.remaining == 120_000


@pytest.mark.asyncio
async def test_a_known_name_reuses_the_person_whatever_the_spelling() -> None:
    """ "juan felipe" is not a new friend — the normalized key dedupes."""
    user_id = new_user_id()
    juan = counterparty(user_id=user_id, name="Juan Felipe")
    people = FakeCounterpartyRepository([juan])

    output = await create(
        creator(FakeDebtRepository(), people),
        user_id=user_id,
        counterparty_name="  juan  FELIPE ",
    )

    assert output.counterparty_id == juan.id
    assert len(await people.list_by_user(user_id)) == 1


@pytest.mark.asyncio
async def test_an_unknown_id_is_rejected() -> None:
    with pytest.raises(CounterpartyNotFoundError):
        await create(
            creator(FakeDebtRepository(), FakeCounterpartyRepository()),
            user_id=new_user_id(),
            counterparty_id="ghost",
        )


@pytest.mark.asyncio
async def test_a_debt_needs_a_person_one_way_or_the_other() -> None:
    with pytest.raises(InvalidDebtError):
        await create(
            creator(FakeDebtRepository(), FakeCounterpartyRepository()),
            user_id=new_user_id(),
        )


@pytest.mark.asyncio
async def test_display_strings_are_not_dates() -> None:
    """The prototype stored "21 may" and `overdue` broke. ISO or nothing."""
    with pytest.raises(InvalidDebtError):
        await create(
            creator(FakeDebtRepository(), FakeCounterpartyRepository()),
            user_id=new_user_id(),
            counterparty_name="Juan",
            due_on="21 may",
        )


@pytest.mark.asyncio
async def test_payments_accumulate_and_the_exact_one_settles() -> None:
    user_id = new_user_id()
    existing = debt(user_id=user_id, amount=120_000)
    debts = FakeDebtRepository([existing])
    pay = AddPaymentUseCase(debt_repository=debts)

    first = await pay.execute(
        AddPaymentInputDTO(user_id=user_id, debt_id=existing.id, today=TODAY, amount=45_000)
    )
    assert (first.status, first.remaining) == ("partial", 75_000)

    second = await pay.execute(
        AddPaymentInputDTO(user_id=user_id, debt_id=existing.id, today=TODAY, amount=75_000)
    )
    assert (second.status, second.remaining) == ("paid", 0)


@pytest.mark.asyncio
async def test_overpaying_is_rejected_not_clamped() -> None:
    user_id = new_user_id()
    existing = debt(user_id=user_id, amount=120_000, payments=(payment(amount=100_000),))
    pay = AddPaymentUseCase(debt_repository=FakeDebtRepository([existing]))

    with pytest.raises(OverpaidError):
        await pay.execute(
            AddPaymentInputDTO(user_id=user_id, debt_id=existing.id, today=TODAY, amount=20_001)
        )


@pytest.mark.asyncio
async def test_removing_a_payment_raises_what_is_owed_again() -> None:
    user_id = new_user_id()
    typo = payment(amount=90_000)
    existing = debt(user_id=user_id, amount=120_000, payments=(typo,))
    debts = FakeDebtRepository([existing])

    output = await RemovePaymentUseCase(debt_repository=debts).execute(
        RemovePaymentInputDTO(user_id=user_id, debt_id=existing.id, payment_id=typo.id, today=TODAY)
    )

    assert output.remaining == 120_000
    assert output.status == "pending"


@pytest.mark.asyncio
async def test_the_amount_cannot_sink_below_what_was_paid() -> None:
    user_id = new_user_id()
    existing = debt(user_id=user_id, amount=120_000, payments=(payment(amount=100_000),))
    update = UpdateDebtUseCase(debt_repository=FakeDebtRepository([existing]))

    with pytest.raises(InvalidDebtError):
        await update.execute(
            UpdateDebtInputDTO(user_id=user_id, debt_id=existing.id, today=TODAY, amount=90_000)
        )


@pytest.mark.asyncio
async def test_deleting_the_last_debt_takes_the_orphan_event_with_it() -> None:
    user_id = new_user_id()
    from src.modules.debts.domain.entities.shared_event import SharedEvent

    from .fakes import FIXED_NOW

    event = SharedEvent.create(
        user_id=user_id, name="Cena", total=400_000, occurred_on=TODAY, created_at=FIXED_NOW
    )
    last = debt(user_id=user_id, event_id=event.id)
    debts = FakeDebtRepository([last])
    events = FakeEventRepository([event])

    await DeleteDebtUseCase(debt_repository=debts, event_repository=events).execute(
        DeleteDebtInputDTO(user_id=user_id, debt_id=last.id)
    )

    assert await events.list_by_user(user_id) == []


@pytest.mark.asyncio
async def test_deleting_one_of_several_keeps_the_event() -> None:
    user_id = new_user_id()
    from src.modules.debts.domain.entities.shared_event import SharedEvent

    from .fakes import FIXED_NOW

    event = SharedEvent.create(
        user_id=user_id, name="Cena", total=400_000, occurred_on=TODAY, created_at=FIXED_NOW
    )
    one = debt(user_id=user_id, event_id=event.id)
    other = debt(user_id=user_id, event_id=event.id)
    debts = FakeDebtRepository([one, other])
    events = FakeEventRepository([event])

    await DeleteDebtUseCase(debt_repository=debts, event_repository=events).execute(
        DeleteDebtInputDTO(user_id=user_id, debt_id=one.id)
    )

    assert len(await events.list_by_user(user_id)) == 1


@pytest.mark.asyncio
async def test_someone_elses_debt_does_not_exist() -> None:
    existing = debt(user_id=new_user_id())
    pay = AddPaymentUseCase(debt_repository=FakeDebtRepository([existing]))

    with pytest.raises(DebtNotFoundError):
        await pay.execute(
            AddPaymentInputDTO(
                user_id=new_user_id(), debt_id=existing.id, today=TODAY, amount=1_000
            )
        )
