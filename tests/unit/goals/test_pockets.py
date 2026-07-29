"""Opening, funding, emptying and closing pockets — and the rules that guard them.

The money itself is a movements concern (the recorder produces real transfers, and the
e2e against docker proves the balances move); what is asserted here is everything the
pocket owns: the gate, the empty-to-close rule, and never letting a withdrawal exceed
what the transfers put in.
"""

import pytest

from src.modules.goals.application.dto.goal_commands import (
    CreateGoalInputDTO,
    DeleteGoalInputDTO,
    GoalsSnapshotInputDTO,
    MoveFundsInputDTO,
    TopGoalInputDTO,
    UpdateGoalInputDTO,
)
from src.modules.goals.application.use_cases.contribute import ContributeUseCase
from src.modules.goals.application.use_cases.create_goal import CreateGoalUseCase
from src.modules.goals.application.use_cases.delete_goal import DeleteGoalUseCase
from src.modules.goals.application.use_cases.get_goals_snapshot import (
    GetGoalsSnapshotUseCase,
)
from src.modules.goals.application.use_cases.get_top_goal import GetTopGoalUseCase
from src.modules.goals.application.use_cases.update_goal import UpdateGoalUseCase
from src.modules.goals.application.use_cases.withdraw import WithdrawUseCase
from src.modules.goals.domain.errors import (
    GoalArchivedError,
    GoalInsufficientError,
    GoalLimitReachedError,
    GoalNotEmptyError,
    InvalidGoalError,
)

from .fakes import (
    CURRENCY,
    FIXED_NOW,
    FREE_ACTIVE_LIMIT,
    TODAY,
    FakeFundsReader,
    FakeGoalRepository,
    FakeTransferRecorder,
    funds,
    goal,
    new_user_id,
)


def creator(repository: FakeGoalRepository) -> CreateGoalUseCase:
    return CreateGoalUseCase(goal_repository=repository, active_free_limit=FREE_ACTIVE_LIMIT)


async def create(
    use_case: CreateGoalUseCase,
    *,
    user_id,
    name: str = "Viaje a Japón",
    target: int = 12_000_000,
    target_date: str | None = None,
    tier: str = "free",
):
    return await use_case.execute(
        CreateGoalInputDTO(
            user_id=user_id,
            tier=tier,
            currency=CURRENCY,
            today=TODAY,
            name=name,
            target=target,
            target_date=target_date,
        )
    )


@pytest.mark.asyncio
async def test_a_new_pocket_is_empty_and_projects_nothing() -> None:
    output = await create(creator(FakeGoalRepository()), user_id=new_user_id())

    assert output.saved == 0
    assert output.pct == 0
    assert output.projected_on is None
    assert not output.archived


@pytest.mark.asyncio
async def test_free_keeps_one_pocket_open_at_a_time() -> None:
    user_id = new_user_id()
    repository = FakeGoalRepository([goal(user_id=user_id)])

    with pytest.raises(GoalLimitReachedError):
        await create(creator(repository), user_id=user_id, name="Fondo de emergencia")


@pytest.mark.asyncio
async def test_an_archived_pocket_never_counts_against_the_gate() -> None:
    """Closing a finished goal is exactly how a Free user starts the next one."""
    user_id = new_user_id()
    repository = FakeGoalRepository([goal(user_id=user_id, archived_at=FIXED_NOW)])

    output = await create(creator(repository), user_id=user_id, name="Fondo")

    assert output.name == "Fondo"


@pytest.mark.asyncio
async def test_plus_opens_as_many_as_it_likes() -> None:
    user_id = new_user_id()
    repository = FakeGoalRepository([goal(user_id=user_id)])

    output = await create(creator(repository), user_id=user_id, name="Fondo", tier="plus")

    assert output.name == "Fondo"


@pytest.mark.asyncio
async def test_a_display_string_is_not_a_target_date() -> None:
    with pytest.raises(InvalidGoalError):
        await create(creator(FakeGoalRepository()), user_id=new_user_id(), target_date="21 may")


@pytest.mark.asyncio
async def test_a_contribution_records_a_real_transfer_into_the_pocket() -> None:
    user_id = new_user_id()
    existing = goal(user_id=user_id)
    recorder = FakeTransferRecorder()
    use_case = ContributeUseCase(
        goal_repository=FakeGoalRepository([existing]),
        funds_reader=FakeFundsReader({existing.id: funds(existing.id, 500_000)}),
        transfer_recorder=recorder,
    )

    output = await use_case.execute(
        MoveFundsInputDTO(
            user_id=user_id,
            currency=CURRENCY,
            today=TODAY,
            goal_id=existing.id,
            account_id="nequi",
            amount=500_000,
        )
    )

    assert recorder.recorded == [
        {
            "user_id": user_id,
            "currency": CURRENCY,
            "description": existing.name,
            "amount": 500_000,
            "account_id": "nequi",
            "goal_id": existing.id,
            "direction": "in",
            "occurred_on": TODAY,
        }
    ]
    assert output.saved == 500_000


@pytest.mark.asyncio
async def test_an_archived_pocket_takes_no_money() -> None:
    user_id = new_user_id()
    existing = goal(user_id=user_id, archived_at=FIXED_NOW)
    use_case = ContributeUseCase(
        goal_repository=FakeGoalRepository([existing]),
        funds_reader=FakeFundsReader(),
        transfer_recorder=FakeTransferRecorder(),
    )

    with pytest.raises(GoalArchivedError):
        await use_case.execute(
            MoveFundsInputDTO(
                user_id=user_id,
                currency=CURRENCY,
                today=TODAY,
                goal_id=existing.id,
                account_id="nequi",
                amount=100_000,
            )
        )


@pytest.mark.asyncio
async def test_a_withdrawal_cannot_exceed_the_pocket() -> None:
    user_id = new_user_id()
    existing = goal(user_id=user_id)
    recorder = FakeTransferRecorder()
    use_case = WithdrawUseCase(
        goal_repository=FakeGoalRepository([existing]),
        funds_reader=FakeFundsReader({existing.id: funds(existing.id, 300_000)}),
        transfer_recorder=recorder,
    )

    with pytest.raises(GoalInsufficientError):
        await use_case.execute(
            MoveFundsInputDTO(
                user_id=user_id,
                currency=CURRENCY,
                today=TODAY,
                goal_id=existing.id,
                account_id="nequi",
                amount=300_001,
            )
        )
    assert recorder.recorded == []


@pytest.mark.asyncio
async def test_the_exact_withdrawal_empties_the_pocket() -> None:
    user_id = new_user_id()
    existing = goal(user_id=user_id)
    recorder = FakeTransferRecorder()
    use_case = WithdrawUseCase(
        goal_repository=FakeGoalRepository([existing]),
        funds_reader=FakeFundsReader({existing.id: funds(existing.id, 300_000)}),
        transfer_recorder=recorder,
    )

    await use_case.execute(
        MoveFundsInputDTO(
            user_id=user_id,
            currency=CURRENCY,
            today=TODAY,
            goal_id=existing.id,
            account_id="nequi",
            amount=300_000,
        )
    )

    assert recorder.recorded[0]["direction"] == "out"


@pytest.mark.asyncio
async def test_closing_a_pocket_with_money_inside_is_refused() -> None:
    """Money hidden inside an archived goal would be money the app stopped showing."""
    user_id = new_user_id()
    existing = goal(user_id=user_id)
    update = UpdateGoalUseCase(
        goal_repository=FakeGoalRepository([existing]),
        funds_reader=FakeFundsReader({existing.id: funds(existing.id, 1)}),
        active_free_limit=FREE_ACTIVE_LIMIT,
    )

    with pytest.raises(GoalNotEmptyError):
        await update.execute(
            UpdateGoalInputDTO(
                user_id=user_id, tier="free", goal_id=existing.id, today=TODAY, archived=True
            )
        )


@pytest.mark.asyncio
async def test_an_empty_pocket_closes_and_reopening_passes_the_gate() -> None:
    user_id = new_user_id()
    first = goal(user_id=user_id)
    repository = FakeGoalRepository([first])
    update = UpdateGoalUseCase(
        goal_repository=repository,
        funds_reader=FakeFundsReader(),
        active_free_limit=FREE_ACTIVE_LIMIT,
    )

    closed = await update.execute(
        UpdateGoalInputDTO(
            user_id=user_id, tier="free", goal_id=first.id, today=TODAY, archived=True
        )
    )
    assert closed.archived

    # A second pocket opens now that the first is archived…
    second = await create(creator(repository), user_id=user_id, name="Fondo")
    assert second.name == "Fondo"

    # …and reopening the first would exceed Free's single active pocket.
    with pytest.raises(GoalLimitReachedError):
        await update.execute(
            UpdateGoalInputDTO(
                user_id=user_id, tier="free", goal_id=first.id, today=TODAY, archived=False
            )
        )


@pytest.mark.asyncio
async def test_deleting_a_funded_pocket_is_refused() -> None:
    user_id = new_user_id()
    existing = goal(user_id=user_id)
    delete = DeleteGoalUseCase(
        goal_repository=FakeGoalRepository([existing]),
        funds_reader=FakeFundsReader({existing.id: funds(existing.id, 100_000)}),
    )

    with pytest.raises(GoalNotEmptyError):
        await delete.execute(DeleteGoalInputDTO(user_id=user_id, goal_id=existing.id))


@pytest.mark.asyncio
async def test_the_snapshot_floats_active_pockets_above_the_archive() -> None:
    user_id = new_user_id()
    archived = goal(user_id=user_id, name="Lograda", archived_at=FIXED_NOW)
    active = goal(user_id=user_id, name="Viaje")
    snapshot = GetGoalsSnapshotUseCase(
        goal_repository=FakeGoalRepository([archived, active]),
        funds_reader=FakeFundsReader({active.id: funds(active.id, 4_100_000)}),
    )

    output = await snapshot.execute(
        GoalsSnapshotInputDTO(user_id=user_id, currency=CURRENCY, today=TODAY)
    )

    assert [g.name for g in output.goals] == ["Viaje", "Lograda"]
    assert output.goals[0].saved == 4_100_000
    assert output.goals[1].archived


@pytest.mark.asyncio
async def test_home_gets_the_pocket_closest_to_done() -> None:
    user_id = new_user_id()
    far = goal(user_id=user_id, name="Viaje", target=12_000_000)
    near = goal(user_id=user_id, name="Fondo", target=1_000_000)
    top = GetTopGoalUseCase(
        goal_repository=FakeGoalRepository([far, near]),
        funds_reader=FakeFundsReader(
            {far.id: funds(far.id, 4_100_000), near.id: funds(near.id, 900_000)}
        ),
    )

    output = await top.execute(TopGoalInputDTO(user_id=user_id, today=TODAY))

    assert output is not None
    assert output.name == "Fondo"  # 90% beats 34%


@pytest.mark.asyncio
async def test_home_gets_nothing_when_every_pocket_is_archived() -> None:
    user_id = new_user_id()
    top = GetTopGoalUseCase(
        goal_repository=FakeGoalRepository([goal(user_id=user_id, archived_at=FIXED_NOW)]),
        funds_reader=FakeFundsReader(),
    )

    assert await top.execute(TopGoalInputDTO(user_id=user_id, today=TODAY)) is None
