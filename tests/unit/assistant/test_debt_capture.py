"""Capturing a debt by voice — and the reason it needed its own tool.

"Le presté 50 mil a Andrés" used to come back as an expense, and not because the
model misread it: the capture loop FORCED `stage_movement_draft` on the first call,
so a debt was not something it could legally say. The fix is two-sided — a debt tool
to say it with, and a forced-ANY first call so the sentence picks the tool.

The money rule underneath is the one the whole debts module is built on: lending is
not spending. The cash becomes a claim, the user is no poorer, and the expense only
ever appears if the debt is written off.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.modules.assistant.application.dto.debt_draft_commands import (
    ConfirmDebtDraftInputDTO,
    DiscardDebtDraftInputDTO,
)
from src.modules.assistant.application.dto.parse import ParseCaptureInputDTO
from src.modules.assistant.application.ports.agent_model import ToolCall
from src.modules.assistant.application.ports.debts_reader import DebtView, PersonView
from src.modules.assistant.application.services.tool_registry import ToolContext
from src.modules.assistant.application.use_cases.confirm_debt_draft import (
    ConfirmDebtDraftUseCase,
)
from src.modules.assistant.application.use_cases.discard_debt_draft import (
    DiscardDebtDraftUseCase,
)
from src.modules.assistant.application.use_cases.parse_capture import ParseCaptureUseCase
from src.modules.assistant.domain.entities.debt_draft import DebtDraft
from src.modules.assistant.domain.errors import (
    DebtPaymentAccountRequiredError,
    DraftNotFoundError,
)

from .fakes import (
    ACCOUNT_ID,
    CURRENCY,
    PLAN_LIMITS,
    PRICING,
    TODAY,
    USER_ID,
    FakeAccountsReader,
    FakeActionLog,
    FakeAgentModel,
    FakeCategoriesReader,
    FakeDebtDrafts,
    FakeDebtPaymentRecorder,
    FakeDebtRecorder,
    FakeDebtsReader,
    FakeDrafts,
    FakeUnitOfWork,
    FakeUsageCounters,
    registry,
    turn,
)

ANDRES = PersonView(id="person-andres", name="Andrés")
SANTIAGO = PersonView(id="person-santiago", name="Santiago")


def _open_debt(**overrides: object) -> DebtView:
    base: dict[str, object] = {
        "id": "debt-1",
        "direction": "owed_to_me",
        "counterparty": "Santiago",
        "amount": 5_000,
        "paid_total": 0,
        "remaining": 5_000,
        "status": "pending",
        "due_on": None,
    }
    base.update(overrides)
    return DebtView(**base)  # type: ignore[arg-type]


def _capture(
    model: FakeAgentModel,
    *,
    people: tuple[PersonView, ...] = (),
    debts: tuple[DebtView, ...] = (),
):
    drafts = FakeDrafts()
    debt_drafts = FakeDebtDrafts()
    usage = FakeUsageCounters()
    case = ParseCaptureUseCase(
        agent_model=model,
        tool_registry=registry(debts=FakeDebtsReader(people, debts)),
        drafts=drafts,
        debt_drafts=debt_drafts,
        usage_counters=usage,
        action_log=FakeActionLog(),
        unit_of_work=FakeUnitOfWork(),
        accounts_reader=FakeAccountsReader(),
        categories_reader=FakeCategoriesReader(),
        plan_limits=PLAN_LIMITS,
        pricing=PRICING,
        model_name="fake-model",
    )
    return case, drafts, debt_drafts, usage


def _input(text: str = "le presté 50 mil a Andrés") -> ParseCaptureInputDTO:
    return ParseCaptureInputDTO(
        user_id=USER_ID,
        currency=CURRENCY,
        tier="free",
        language="es",
        objective=None,
        today=TODAY,
        text=text,
        source="voice",
    )


def _debt_turn(**arguments: object):
    base: dict[str, object] = {
        "direction": "incoming",
        "counterparty_name": "Andrés",
        "amount": "50000",
    }
    base.update(arguments)
    return turn(tool_calls=(ToolCall(id="d1", name="stage_debt_draft", arguments=base),))


@pytest.mark.asyncio
async def test_lending_comes_back_as_a_debt_and_never_as_an_expense() -> None:
    case, drafts, debt_drafts, _ = _capture(FakeAgentModel([_debt_turn()]))

    output = await case.execute(_input())

    assert output.drafts == []
    assert len(output.debt_drafts) == 1
    assert output.debt_drafts[0].direction == "incoming"
    assert output.debt_drafts[0].amount == 50_000
    assert drafts.saved == []
    assert debt_drafts.saved[0].captured_via == "voice"


@pytest.mark.asyncio
async def test_a_debt_costs_one_registration_like_any_capture() -> None:
    case, _, _, usage = _capture(FakeAgentModel([_debt_turn()]))

    output = await case.execute(_input())

    assert usage.consumed == [{"registrations": 1, "messages": 0}]
    assert output.usage.registrations.used == 1


@pytest.mark.asyncio
async def test_a_name_already_in_the_ledger_resolves_to_that_person() -> None:
    """The one place the agent IS allowed to decide: creating a second "Andrés"
    would split his debts across two people who are the same person."""
    case, _, _, _ = _capture(FakeAgentModel([_debt_turn()]), people=(ANDRES,))

    output = await case.execute(_input())

    assert output.debt_drafts[0].counterparty_id == ANDRES.id


@pytest.mark.asyncio
async def test_a_name_matches_however_it_was_capitalised() -> None:
    case, _, _, _ = _capture(
        FakeAgentModel([_debt_turn(counterparty_name="andrés")]), people=(ANDRES,)
    )

    output = await case.execute(_input())

    assert output.debt_drafts[0].counterparty_id == ANDRES.id


@pytest.mark.asyncio
async def test_a_stranger_stays_a_name_and_becomes_a_person_on_confirm() -> None:
    case, _, _, _ = _capture(FakeAgentModel([_debt_turn(counterparty_name="Sofía")]))

    output = await case.execute(_input())

    assert output.debt_drafts[0].counterparty_id is None
    assert output.debt_drafts[0].counterparty_name == "Sofía"


@pytest.mark.asyncio
async def test_an_unnamed_account_is_left_for_the_card_to_ask() -> None:
    """Same rule as a movement: guessing which account the money left reads as the
    app deciding for you, and a wrong guess moves a real balance."""
    case, _, _, _ = _capture(FakeAgentModel([_debt_turn()]))

    output = await case.execute(_input())

    assert output.debt_drafts[0].account_id is None


@pytest.mark.asyncio
async def test_one_breath_can_hold_a_debt_and_an_expense() -> None:
    """People do not sort their sentences by our tools: 'me tomé un café de 5 mil y
    le presté 50 a Andrés' is both, in one turn."""
    both = turn(
        tool_calls=(
            ToolCall(
                id="m1",
                name="stage_movement_draft",
                arguments={
                    "type": "expense",
                    "amount": "5000",
                    "description": "Café",
                    "source_id": ACCOUNT_ID,
                },
            ),
            ToolCall(
                id="d1",
                name="stage_debt_draft",
                arguments={
                    "direction": "incoming",
                    "counterparty_name": "Andrés",
                    "amount": "50000",
                },
            ),
        )
    )
    case, _, _, usage = _capture(FakeAgentModel([both]))

    output = await case.execute(_input("me tomé un café de 5 mil y le presté 50 a Andrés"))

    assert len(output.drafts) == 1
    assert len(output.debt_drafts) == 1
    # Two captures, two registrations: the quota counts what was recorded.
    assert usage.consumed == [{"registrations": 2, "messages": 0}]


@pytest.mark.asyncio
async def test_an_unknown_account_is_refused_rather_than_silently_dropped() -> None:
    outcome = await registry().execute(
        ToolCall(
            id="d1",
            name="stage_debt_draft",
            arguments={
                "direction": "incoming",
                "counterparty_name": "Andrés",
                "amount": "50000",
                "account_id": "no-existe",
            },
        ),
        _ctx(),
    )

    assert outcome.is_error
    assert outcome.debt_draft is None


@pytest.mark.asyncio
async def test_a_direction_outside_the_two_is_refused() -> None:
    outcome = await registry().execute(
        ToolCall(
            id="d1",
            name="stage_debt_draft",
            arguments={
                "direction": "sideways",
                "counterparty_name": "Andrés",
                "amount": "50000",
            },
        ),
        _ctx(),
    )

    assert outcome.is_error


def _draft(**overrides: object) -> DebtDraft:
    base: dict[str, object] = {
        "user_id": USER_ID,
        "currency": CURRENCY,
        "direction": "incoming",
        "counterparty_id": None,
        "counterparty_name": "Andrés",
        "amount": 50_000,
        "account_id": None,
        "kind": "new",
        "target_debt_id": None,
        "due_on": None,
        "note": None,
        "created_at": datetime(2026, 7, 27, tzinfo=UTC),
    }
    base.update(overrides)
    return DebtDraft.stage(**base)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_confirming_answers_the_account_the_card_asked_for() -> None:
    staged = _draft()
    store = FakeDebtDrafts([staged])
    recorder = FakeDebtRecorder()

    output = await ConfirmDebtDraftUseCase(
        debt_drafts=store,
        debt_recorder=recorder,
        payment_recorder=FakeDebtPaymentRecorder(),
    ).execute(
        ConfirmDebtDraftInputDTO(
            user_id=USER_ID, draft_id=staged.id, today=TODAY, account_id=ACCOUNT_ID
        )
    )

    assert recorder.recorded[0]["account_id"] == ACCOUNT_ID
    assert output.draft.status == "confirmed"
    assert output.debt_id == recorder.recorded[0]["debt_id"]


@pytest.mark.asyncio
async def test_no_money_moved_is_a_real_answer_not_a_missing_one() -> None:
    """A dinner split: the bill already left as one expense, so the debt records who
    owes what and moves nothing. Sending `account_id: null` says exactly that."""
    staged = _draft(account_id=ACCOUNT_ID)
    store = FakeDebtDrafts([staged])
    recorder = FakeDebtRecorder()

    await ConfirmDebtDraftUseCase(
        debt_drafts=store,
        debt_recorder=recorder,
        payment_recorder=FakeDebtPaymentRecorder(),
    ).execute(
        ConfirmDebtDraftInputDTO(
            user_id=USER_ID,
            draft_id=staged.id,
            today=TODAY,
            account_id=None,
            clear_account=True,
        )
    )

    assert recorder.recorded[0]["account_id"] is None


@pytest.mark.asyncio
async def test_a_known_person_is_named_by_id_and_never_created_twice() -> None:
    staged = _draft(counterparty_id=ANDRES.id)
    recorder = FakeDebtRecorder()

    await ConfirmDebtDraftUseCase(
        debt_drafts=FakeDebtDrafts([staged]),
        debt_recorder=recorder,
        payment_recorder=FakeDebtPaymentRecorder(),
    ).execute(ConfirmDebtDraftInputDTO(user_id=USER_ID, draft_id=staged.id, today=TODAY))

    assert recorder.recorded[0]["counterparty_id"] == ANDRES.id
    assert recorder.recorded[0]["counterparty_name"] is None


@pytest.mark.asyncio
async def test_someone_elses_draft_does_not_exist() -> None:
    staged = _draft()

    with pytest.raises(DraftNotFoundError):
        await ConfirmDebtDraftUseCase(
            debt_drafts=FakeDebtDrafts([staged]),
            debt_recorder=FakeDebtRecorder(),
            payment_recorder=FakeDebtPaymentRecorder(),
        ).execute(ConfirmDebtDraftInputDTO(user_id=uuid4(), draft_id=staged.id, today=TODAY))


@pytest.mark.asyncio
async def test_discarding_never_touches_the_ledger() -> None:
    staged = _draft()
    store = FakeDebtDrafts([staged])

    output = await DiscardDebtDraftUseCase(debt_drafts=store).execute(
        DiscardDebtDraftInputDTO(user_id=USER_ID, draft_id=staged.id)
    )

    assert output.draft.status == "discarded"


# ── Abonar una deuda que ya existe ────────────────────────────────────────────
#
# The shipped bug: "Santiago me pagó $2.000" had no tool that fit, so the agent did
# the closest thing available and opened a SECOND debt for Santiago — with the note
# "Pago de deuda", which is the model telling you exactly what it meant and being
# unable to say it. The card then asked "¿de qué cuenta SALIÓ?" over money that was
# coming IN. Both are the same root cause: a missing verb.


def _ctx() -> ToolContext:
    return ToolContext(
        user_id=USER_ID,
        currency=CURRENCY,
        today=TODAY,
        registrations_used=0,
        registrations_limit=100,
        staged_count=0,
    )


def _payment_turn(**arguments: object):
    base: dict[str, object] = {"counterparty_name": "Santiago", "amount": "2000"}
    base.update(arguments)
    return turn(tool_calls=(ToolCall(id="p1", name="stage_debt_payment_draft", arguments=base),))


@pytest.mark.asyncio
async def test_being_paid_back_pays_the_debt_down_instead_of_opening_another() -> None:
    case, _, _, _ = _capture(
        FakeAgentModel([_payment_turn()]),
        people=(SANTIAGO,),
        debts=(_open_debt(),),
    )

    output = await case.execute(_input("Santiago me pagó 2.000 de la deuda"))

    assert len(output.debt_drafts) == 1
    staged = output.debt_drafts[0]
    assert staged.kind == "payment"
    assert staged.target_debt_id == "debt-1"
    assert staged.amount == 2_000


@pytest.mark.asyncio
async def test_the_payment_carries_the_debts_own_direction() -> None:
    """It decides which way the cash flows back — and so which question the card
    asks. Getting it backwards is what put "¿de qué cuenta salió?" over money
    that was landing."""
    case, _, _, _ = _capture(
        FakeAgentModel([_payment_turn()]), people=(SANTIAGO,), debts=(_open_debt(),)
    )

    output = await case.execute(_input())

    assert output.debt_drafts[0].direction == "incoming"


@pytest.mark.asyncio
async def test_paying_someone_with_no_open_debt_is_refused_not_invented() -> None:
    """The exact wrong turn: with nothing to pay, opening a debt to pay it off is
    not a fallback, it is a fabrication."""
    outcome = await registry(debts=FakeDebtsReader()).execute(
        ToolCall(
            id="p1",
            name="stage_debt_payment_draft",
            arguments={"counterparty_name": "Santiago", "amount": "2000"},
        ),
        _ctx(),
    )

    assert outcome.is_error
    assert outcome.debt_draft is None
    assert "no_open_debt" in outcome.content


@pytest.mark.asyncio
async def test_two_open_debts_leave_the_target_for_the_card_to_ask() -> None:
    """Paying down the wrong side of a two-way friendship is a mistake nobody would
    spot for months — so it is not guessed. But the question belongs to the CARD,
    not to the agent's words: the app has the list, the user does not have to
    remember it."""
    reader = FakeDebtsReader(
        (SANTIAGO,),
        (
            _open_debt(id="d-owed", direction="owed_to_me"),
            _open_debt(id="d-owing", direction="i_owe"),
        ),
    )
    outcome = await registry(debts=reader).execute(
        ToolCall(
            id="p1",
            name="stage_debt_payment_draft",
            arguments={"counterparty_name": "Santiago", "amount": "2000"},
        ),
        _ctx(),
    )

    assert not outcome.is_error
    assert outcome.debt_draft is not None
    assert outcome.debt_draft.target_debt_id is None


@pytest.mark.asyncio
async def test_saying_no_name_at_all_still_stages_the_abono() -> None:
    """ "Me pagaron 2.000 de una deuda" names nobody, and that is not a failure to
    understand — it is how people talk. Falling back to asking in words is what put
    the sentence back in the text box and did nothing."""
    reader = FakeDebtsReader(
        (SANTIAGO, ANDRES),
        (
            _open_debt(id="d-santiago", counterparty="Santiago"),
            _open_debt(id="d-andres", counterparty="Andrés"),
        ),
    )
    outcome = await registry(debts=reader).execute(
        ToolCall(id="p1", name="stage_debt_payment_draft", arguments={"amount": "2000"}),
        _ctx(),
    )

    assert not outcome.is_error
    assert outcome.debt_draft is not None
    assert outcome.debt_draft.target_debt_id is None
    assert outcome.debt_draft.amount == 2_000


@pytest.mark.asyncio
async def test_no_name_and_a_single_open_debt_is_not_a_choice() -> None:
    """A list of one is not a question. Same rule the source picker follows."""
    reader = FakeDebtsReader((SANTIAGO,), (_open_debt(id="d-only"),))
    outcome = await registry(debts=reader).execute(
        ToolCall(id="p1", name="stage_debt_payment_draft", arguments={"amount": "2000"}),
        _ctx(),
    )

    assert outcome.debt_draft is not None
    assert outcome.debt_draft.target_debt_id == "d-only"
    assert outcome.debt_draft.counterparty_name == "Santiago"


@pytest.mark.asyncio
async def test_nobody_owes_anything_so_there_is_nothing_to_pay() -> None:
    outcome = await registry(debts=FakeDebtsReader()).execute(
        ToolCall(id="p1", name="stage_debt_payment_draft", arguments={"amount": "2000"}),
        _ctx(),
    )

    assert outcome.is_error
    assert "no_open_debt" in outcome.content


@pytest.mark.asyncio
async def test_paying_more_than_is_left_is_refused_rather_than_clamped() -> None:
    outcome = await registry(
        debts=FakeDebtsReader((SANTIAGO,), (_open_debt(remaining=1_000),))
    ).execute(
        ToolCall(
            id="p1",
            name="stage_debt_payment_draft",
            arguments={"counterparty_name": "Santiago", "amount": "2000"},
        ),
        _ctx(),
    )

    assert outcome.is_error
    assert "more_than_owed" in outcome.content


@pytest.mark.asyncio
async def test_confirming_a_payment_pays_the_debt_and_creates_nothing() -> None:
    staged = _draft(kind="payment", target_debt_id="debt-1", account_id=ACCOUNT_ID, amount=2_000)
    opener = FakeDebtRecorder()
    payer = FakeDebtPaymentRecorder()

    output = await ConfirmDebtDraftUseCase(
        debt_drafts=FakeDebtDrafts([staged]),
        debt_recorder=opener,
        payment_recorder=payer,
    ).execute(ConfirmDebtDraftInputDTO(user_id=USER_ID, draft_id=staged.id, today=TODAY))

    assert payer.recorded[0]["debt_id"] == "debt-1"
    assert payer.recorded[0]["amount"] == 2_000
    # The whole point: no second debt for the same person.
    assert opener.recorded == []
    assert output.debt_id == "debt-1"


@pytest.mark.asyncio
async def test_a_repayment_cannot_confirm_without_an_account() -> None:
    """ "No money moved" is not an answer to being paid back, it is a contradiction —
    unlike a loan, which may honestly never have moved any."""
    staged = _draft(kind="payment", target_debt_id="debt-1", account_id=None)

    with pytest.raises(DebtPaymentAccountRequiredError):
        await ConfirmDebtDraftUseCase(
            debt_drafts=FakeDebtDrafts([staged]),
            debt_recorder=FakeDebtRecorder(),
            payment_recorder=FakeDebtPaymentRecorder(),
        ).execute(ConfirmDebtDraftInputDTO(user_id=USER_ID, draft_id=staged.id, today=TODAY))


@pytest.mark.asyncio
async def test_confirming_an_abono_hands_back_the_movement_to_undo() -> None:
    """Undo means deleting THAT movement, and the debt has to survive it. A caller
    holding only the debt id would have to guess which of its instalments was new —
    or worse, delete the debt to undo a repayment."""
    staged = _draft(kind="payment", target_debt_id="debt-1", account_id=ACCOUNT_ID, amount=2_000)
    payer = FakeDebtPaymentRecorder()

    output = await ConfirmDebtDraftUseCase(
        debt_drafts=FakeDebtDrafts([staged]),
        debt_recorder=FakeDebtRecorder(),
        payment_recorder=payer,
    ).execute(ConfirmDebtDraftInputDTO(user_id=USER_ID, draft_id=staged.id, today=TODAY))

    assert output.movement_id == "mov-abono-1"
    assert output.debt_id == "debt-1"


@pytest.mark.asyncio
async def test_opening_a_debt_hands_back_no_movement_because_undo_is_the_debt() -> None:
    """Deleting the debt reverts its loan transfer with it, so there is nothing
    separate to point at — and `movement_id` staying null is the flag that says
    which of the two undos applies."""
    staged = _draft(account_id=ACCOUNT_ID)

    output = await ConfirmDebtDraftUseCase(
        debt_drafts=FakeDebtDrafts([staged]),
        debt_recorder=FakeDebtRecorder(),
        payment_recorder=FakeDebtPaymentRecorder(),
    ).execute(ConfirmDebtDraftInputDTO(user_id=USER_ID, draft_id=staged.id, today=TODAY))

    assert output.movement_id is None
