"""The charge engine: ask first, register if nobody answers.

This is the one part of the app that spends money without a person pressing save, so
the tests are about the guarantees that make that acceptable: it asks first, it never
charges the same day twice, it can be skipped, and a paused or deleted subscription
stops it.
"""

from datetime import timedelta
from uuid import uuid4

import pytest

from src.modules.subscriptions.application.dto.charge import (
    ListChargesInputDTO,
    SettleChargeInputDTO,
)
from src.modules.subscriptions.application.services.charge_settlement import ChargeSettlement
from src.modules.subscriptions.application.use_cases.confirm_charge import ConfirmChargeUseCase
from src.modules.subscriptions.application.use_cases.list_charges import ListChargesUseCase
from src.modules.subscriptions.application.use_cases.open_due_charges import (
    OpenDueChargesUseCase,
)
from src.modules.subscriptions.application.use_cases.settle_unconfirmed_charges import (
    SettleUnconfirmedChargesUseCase,
)
from src.modules.subscriptions.application.use_cases.skip_charge import SkipChargeUseCase
from src.modules.subscriptions.domain.errors import (
    ChargeAlreadySettledError,
    ChargeNotFoundError,
)
from src.modules.subscriptions.domain.schedule import CONFIRMATION_WINDOW_HOURS

from .fakes import (
    CARD,
    FIXED_NOW,
    TODAY,
    FakeChargeRepository,
    FakeExpenseRecorder,
    FakeSubscriptionRepository,
    FixedClock,
    ImmediateUnitOfWork,
    charge,
    subscription,
)

YESTERDAY = "2026-07-25"
A_WEEK_BEFORE = "2026-07-18"


def wire(*, subscriptions=None, charges=None, now=FIXED_NOW):
    subs_repo = FakeSubscriptionRepository(subscriptions or [])
    charge_repo = FakeChargeRepository(charges or [])
    recorder = FakeExpenseRecorder()
    clock = FixedClock(now)
    settlement = ChargeSettlement(
        charge_repository=charge_repo,
        subscription_repository=subs_repo,
        expense_recorder=recorder,
        unit_of_work=ImmediateUnitOfWork(),
        clock=clock,
    )
    return {
        "subs_repo": subs_repo,
        "charge_repo": charge_repo,
        "recorder": recorder,
        "open": OpenDueChargesUseCase(
            subscription_repository=subs_repo, charge_repository=charge_repo, clock=clock
        ),
        "settle": SettleUnconfirmedChargesUseCase(
            charge_repository=charge_repo, settlement=settlement, clock=clock
        ),
        "confirm": ConfirmChargeUseCase(charge_repository=charge_repo, settlement=settlement),
        "skip": SkipChargeUseCase(charge_repository=charge_repo, settlement=settlement),
        "list": ListChargesUseCase(charge_repository=charge_repo),
    }


# ── opening ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_charge_due_today_opens_as_pending() -> None:
    sub = subscription(first_charge_on=TODAY, created_at=FIXED_NOW - timedelta(days=30))
    app = wire(subscriptions=[sub])

    assert await app["open"].execute() == 1

    opened = app["charge_repo"].charges[0]
    assert (opened.status, opened.due_on, opened.amount) == ("pending", TODAY, sub.amount)
    assert app["recorder"].recorded == []  # nothing charged yet: it asks first


@pytest.mark.asyncio
async def test_opening_twice_does_not_charge_twice() -> None:
    """The unique index is the guard; a second hourly run must be a no-op."""
    sub = subscription(first_charge_on=TODAY, created_at=FIXED_NOW - timedelta(days=30))
    app = wire(subscriptions=[sub])

    assert await app["open"].execute() == 1
    assert await app["open"].execute() == 0
    assert len(app["charge_repo"].charges) == 1


@pytest.mark.asyncio
async def test_a_paused_subscription_opens_nothing() -> None:
    sub = subscription(
        first_charge_on=TODAY, active=False, created_at=FIXED_NOW - timedelta(days=30)
    )
    app = wire(subscriptions=[sub])

    assert await app["open"].execute() == 0


@pytest.mark.asyncio
async def test_a_missed_day_is_caught_up_but_old_ones_are_not() -> None:
    """A worker down for an hour must not skip a charge; one down for a month must
    not dump thirty of them."""
    # Every Saturday, so the 18th and the 25th are both in the past on Sunday 26th.
    weekly = subscription(
        frequency="weekly",
        first_charge_on="2026-06-06",
        created_at=FIXED_NOW - timedelta(days=60),
    )
    app = wire(subscriptions=[weekly])

    await app["open"].execute()

    due = [c.due_on for c in app["charge_repo"].charges]
    assert due == [YESTERDAY]  # inside the two-day catch-up
    assert A_WEEK_BEFORE not in due  # older than that is left alone


@pytest.mark.asyncio
async def test_nothing_is_charged_for_a_date_before_the_subscription_existed() -> None:
    """An anchor in the past is legitimate; six months of retroactive expenses are not."""
    sub = subscription(
        frequency="weekly",
        first_charge_on="2026-01-01",
        created_at=FIXED_NOW,  # registered today
    )
    app = wire(subscriptions=[sub])

    await app["open"].execute()

    assert [c.due_on for c in app["charge_repo"].charges] == []


# ── the confirmation window ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inside_the_window_nothing_is_registered() -> None:
    sub = subscription()
    pending = charge(user_id=sub.user_id, subscription_id=sub.id, opened_at=FIXED_NOW)
    app = wire(
        subscriptions=[sub],
        charges=[pending],
        now=FIXED_NOW + timedelta(hours=CONFIRMATION_WINDOW_HOURS - 1),
    )

    assert await app["settle"].execute() == 0
    assert app["charge_repo"].charges[0].status == "pending"


@pytest.mark.asyncio
async def test_once_the_window_closes_the_charge_is_registered_as_auto() -> None:
    sub = subscription()
    pending = charge(user_id=sub.user_id, subscription_id=sub.id, opened_at=FIXED_NOW)
    app = wire(
        subscriptions=[sub],
        charges=[pending],
        now=FIXED_NOW + timedelta(hours=CONFIRMATION_WINDOW_HOURS + 1),
    )

    assert await app["settle"].execute() == 1

    settled = app["charge_repo"].charges[0]
    assert settled.status == "auto"
    assert settled.movement_id == "mov-1"
    assert app["recorder"].recorded[0]["description"] == sub.name
    assert app["recorder"].recorded[0]["occurred_on"] == pending.due_on


@pytest.mark.asyncio
async def test_settling_twice_produces_a_single_movement() -> None:
    """The idempotency key is derived from the charge, so a retry replays it."""
    sub = subscription()
    pending = charge(user_id=sub.user_id, subscription_id=sub.id, opened_at=FIXED_NOW)
    app = wire(
        subscriptions=[sub],
        charges=[pending],
        now=FIXED_NOW + timedelta(hours=CONFIRMATION_WINDOW_HOURS + 1),
    )

    await app["settle"].execute()
    await app["settle"].execute()

    assert len(app["recorder"].recorded) == 1


@pytest.mark.asyncio
async def test_the_expense_lands_on_the_card_the_subscription_uses() -> None:
    sub = subscription(source=CARD)
    pending = charge(user_id=sub.user_id, subscription_id=sub.id, opened_at=FIXED_NOW)
    app = wire(
        subscriptions=[sub],
        charges=[pending],
        now=FIXED_NOW + timedelta(hours=CONFIRMATION_WINDOW_HOURS + 1),
    )

    await app["settle"].execute()

    assert app["recorder"].recorded[0]["source"] == CARD


@pytest.mark.asyncio
async def test_a_deleted_subscription_leaves_its_charge_unsettled_without_failing() -> None:
    """One user's mess must not stop everyone else's charges."""
    orphan = charge(user_id=uuid4(), subscription_id="gone", opened_at=FIXED_NOW)
    app = wire(charges=[orphan], now=FIXED_NOW + timedelta(hours=CONFIRMATION_WINDOW_HOURS + 1))

    assert await app["settle"].execute() == 0
    assert app["recorder"].recorded == []


# ── confirming and skipping ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirming_registers_the_expense_now() -> None:
    sub = subscription()
    pending = charge(user_id=sub.user_id, subscription_id=sub.id)
    app = wire(subscriptions=[sub], charges=[pending])

    output = await app["confirm"].execute(
        SettleChargeInputDTO(user_id=sub.user_id, charge_id=pending.id)
    )

    assert output.status == "confirmed"
    assert output.movement_id == "mov-1"


@pytest.mark.asyncio
async def test_confirming_a_different_amount_records_what_really_happened() -> None:
    """Netflix raised its price: the movement is the truth, not the forecast."""
    sub = subscription(amount=30_900)
    pending = charge(user_id=sub.user_id, subscription_id=sub.id, amount=30_900)
    app = wire(subscriptions=[sub], charges=[pending])

    output = await app["confirm"].execute(
        SettleChargeInputDTO(user_id=sub.user_id, charge_id=pending.id, amount=44_900)
    )

    assert output.amount == 44_900
    assert app["recorder"].recorded[0]["amount"] == 44_900


@pytest.mark.asyncio
async def test_confirming_twice_is_refused_instead_of_charging_again() -> None:
    sub = subscription()
    pending = charge(user_id=sub.user_id, subscription_id=sub.id)
    app = wire(subscriptions=[sub], charges=[pending])
    await app["confirm"].execute(SettleChargeInputDTO(user_id=sub.user_id, charge_id=pending.id))

    with pytest.raises(ChargeAlreadySettledError):
        await app["confirm"].execute(
            SettleChargeInputDTO(user_id=sub.user_id, charge_id=pending.id)
        )

    assert len(app["recorder"].recorded) == 1


@pytest.mark.asyncio
async def test_skipping_never_produces_a_movement() -> None:
    sub = subscription()
    pending = charge(user_id=sub.user_id, subscription_id=sub.id)
    app = wire(subscriptions=[sub], charges=[pending])

    output = await app["skip"].execute(
        SettleChargeInputDTO(user_id=sub.user_id, charge_id=pending.id)
    )

    assert output.status == "skipped"
    assert output.movement_id is None
    assert app["recorder"].recorded == []


@pytest.mark.asyncio
async def test_a_skipped_charge_is_not_settled_later_by_the_job() -> None:
    sub = subscription()
    pending = charge(user_id=sub.user_id, subscription_id=sub.id, opened_at=FIXED_NOW)
    app = wire(
        subscriptions=[sub],
        charges=[pending],
        now=FIXED_NOW + timedelta(hours=CONFIRMATION_WINDOW_HOURS + 1),
    )
    await app["skip"].execute(SettleChargeInputDTO(user_id=sub.user_id, charge_id=pending.id))

    assert await app["settle"].execute() == 0
    assert app["recorder"].recorded == []


@pytest.mark.asyncio
async def test_another_tenants_charge_is_not_found() -> None:
    sub = subscription()
    pending = charge(user_id=sub.user_id, subscription_id=sub.id)
    app = wire(subscriptions=[sub], charges=[pending])

    with pytest.raises(ChargeNotFoundError):
        await app["confirm"].execute(SettleChargeInputDTO(user_id=uuid4(), charge_id=pending.id))


@pytest.mark.asyncio
async def test_the_pending_list_is_scoped_and_filtered() -> None:
    mine, theirs = uuid4(), uuid4()
    app = wire(
        charges=[
            charge(user_id=mine, subscription_id="a", due_on="2026-07-26"),
            charge(user_id=mine, subscription_id="b", due_on="2026-07-24", status="auto"),
            charge(user_id=theirs, subscription_id="c"),
        ]
    )

    everything = await app["list"].execute(ListChargesInputDTO(user_id=mine))
    pending = await app["list"].execute(ListChargesInputDTO(user_id=mine, status="pending"))

    assert len(everything.charges) == 2
    assert [c.due_on for c in everything.charges] == ["2026-07-24", "2026-07-26"]
    assert len(pending.charges) == 1
