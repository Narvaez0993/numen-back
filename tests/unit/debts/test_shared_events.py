"""The dinner, split — the math happens once, at creation, and produces plain debts.

The user's own share is the difference between the total and the splits: it is not a
debt, so nothing stores it. Every failure below leaves nothing behind (all writes are
inside the unit of work, and validation happens before it).
"""

import pytest

from src.modules.debts.application.dto.debt_commands import (
    CreateSharedEventInputDTO,
    DebtsSnapshotInputDTO,
    SplitInputDTO,
)
from src.modules.debts.application.services.counterparty_resolver import (
    CounterpartyResolver,
)
from src.modules.debts.application.use_cases.create_shared_event import (
    CreateSharedEventUseCase,
)
from src.modules.debts.application.use_cases.get_debts_snapshot import (
    GetDebtsSnapshotUseCase,
)
from src.modules.debts.domain.errors import InvalidDebtError

from .fakes import (
    CURRENCY,
    TODAY,
    FakeCounterpartyRepository,
    FakeDebtRepository,
    FakeEventRepository,
    ImmediateUnitOfWork,
    new_user_id,
)


def build(
    debts: FakeDebtRepository | None = None,
    people: FakeCounterpartyRepository | None = None,
    events: FakeEventRepository | None = None,
) -> tuple[CreateSharedEventUseCase, FakeDebtRepository, FakeEventRepository, ImmediateUnitOfWork]:
    debts = debts or FakeDebtRepository()
    people = people or FakeCounterpartyRepository()
    events = events or FakeEventRepository()
    unit_of_work = ImmediateUnitOfWork()
    snapshot = GetDebtsSnapshotUseCase(
        debt_repository=debts,
        counterparty_repository=people,
        event_repository=events,
    )
    use_case = CreateSharedEventUseCase(
        debt_repository=debts,
        event_repository=events,
        counterparty_repository=people,
        counterparty_resolver=CounterpartyResolver(counterparty_repository=people),
        unit_of_work=unit_of_work,
        snapshot=snapshot,
    )
    return use_case, debts, events, unit_of_work


def splits(*shares: tuple[str, int]) -> list[SplitInputDTO]:
    return [SplitInputDTO(counterparty_name=name, amount=amount) for name, amount in shares]


async def create(
    use_case: CreateSharedEventUseCase,
    *,
    user_id,
    total: int = 400_000,
    shares: list[SplitInputDTO] | None = None,
    name: str = "Cena del viernes",
):
    return await use_case.execute(
        CreateSharedEventInputDTO(
            user_id=user_id,
            currency=CURRENCY,
            today=TODAY,
            direction="incoming",
            name=name,
            total=total,
            due_on=None,
            splits=shares
            if shares is not None
            else splits(("Juan", 100_000), ("María", 100_000), ("Camila", 100_000)),
        )
    )


@pytest.mark.asyncio
async def test_one_event_and_a_debt_per_person_written_in_one_unit() -> None:
    user_id = new_user_id()
    use_case, debts, events, unit_of_work = build()

    output = await create(use_case, user_id=user_id)

    assert unit_of_work.calls == 1
    stored_events = await events.list_by_user(user_id)
    stored_debts = await debts.list_by_user(user_id)
    assert len(stored_events) == 1
    assert stored_events[0].total == 400_000  # the user's own 100.000 included
    assert len(stored_debts) == 3
    assert all(debt.event_id == stored_events[0].id for debt in stored_debts)
    # And the response is the whole snapshot, already consistent.
    assert output.owed_to_me.total == 300_000
    assert output.owed_to_me.count == 3


@pytest.mark.asyncio
async def test_the_users_own_share_is_nobodys_debt() -> None:
    """$400.000 among 4: three debts of $100.000 — the payer's share is not stored."""
    user_id = new_user_id()
    use_case, debts, _, _ = build()

    await create(use_case, user_id=user_id)

    total_owed = sum(debt.amount for debt in await debts.list_by_user(user_id))
    assert total_owed == 300_000


@pytest.mark.asyncio
async def test_shares_beyond_the_total_are_rejected() -> None:
    use_case, debts, events, _ = build()
    user_id = new_user_id()

    with pytest.raises(InvalidDebtError):
        await create(
            use_case,
            user_id=user_id,
            total=200_000,
            shares=splits(("Juan", 150_000), ("María", 100_000)),
        )

    assert await debts.list_by_user(user_id) == []
    assert await events.list_by_user(user_id) == []


@pytest.mark.asyncio
async def test_a_split_needs_at_least_two_people() -> None:
    use_case, _, _, _ = build()

    with pytest.raises(InvalidDebtError):
        await create(use_case, user_id=new_user_id(), shares=splits(("Juan", 100_000)))


@pytest.mark.asyncio
async def test_a_zero_share_is_not_a_participant() -> None:
    use_case, _, _, _ = build()

    with pytest.raises(InvalidDebtError):
        await create(
            use_case,
            user_id=new_user_id(),
            shares=splits(("Juan", 100_000), ("María", 0)),
        )


@pytest.mark.asyncio
async def test_the_same_person_cannot_appear_twice() -> None:
    """ "juan" and "JUAN" resolve to one counterparty — a duplicate split is a typo."""
    use_case, _, _, _ = build()

    with pytest.raises(InvalidDebtError):
        await create(
            use_case,
            user_id=new_user_id(),
            shares=splits(("Juan", 100_000), ("JUAN", 100_000)),
        )


@pytest.mark.asyncio
async def test_the_people_of_a_split_are_created_inline_once() -> None:
    user_id = new_user_id()
    people = FakeCounterpartyRepository()
    use_case, _, _, _ = build(people=people)

    await create(use_case, user_id=user_id)
    # A second dinner with the same friends mints nobody new.
    await create(use_case, user_id=user_id, name="Otra cena")

    assert len(await people.list_by_user(user_id)) == 3


@pytest.mark.asyncio
async def test_snapshot_totals_split_by_direction_and_skip_the_paid() -> None:
    user_id = new_user_id()
    use_case, debts_repo, events_repo, _ = build()

    await create(use_case, user_id=user_id)

    from .fakes import debt as make_debt
    from .fakes import payment

    await debts_repo.save(make_debt(user_id=user_id, direction="outgoing", amount=200_000))
    await debts_repo.save(
        make_debt(
            user_id=user_id,
            direction="incoming",
            amount=50_000,
            payments=(payment(amount=50_000),),
        )
    )

    snapshot = GetDebtsSnapshotUseCase(
        debt_repository=debts_repo,
        counterparty_repository=FakeCounterpartyRepository(),
        event_repository=events_repo,
    )
    output = await snapshot.execute(
        DebtsSnapshotInputDTO(user_id=user_id, currency=CURRENCY, today=TODAY)
    )

    assert output.owed_to_me.total == 300_000  # the paid 50.000 is history
    assert output.owed_to_me.count == 3
    assert output.i_owe.total == 200_000
    assert output.i_owe.count == 1
    # The paid one still travels — the history sheet reads it.
    assert len(output.debts) == 5
