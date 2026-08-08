"""Giving up on a claim — the one moment lending becomes spending.

Everything the module does before this is a transfer: cash turns into a claim and the
user is no poorer. Here the claim dies, so a real expense appears, and the arithmetic
of WHICH expense is the whole risk. Two ways to get it wrong, both silent:

* charging the account again (it was already debited when the money was lent), and
* charging anything at all for a debt that never moved cash — a dinner split, whose
  bill already left as one expense.

The tests below pin both, plus the undo: writing off is a judgement made under
uncertainty, and one the user cannot take back is one they will not make.
"""

import pytest

from src.modules.debts.application.dto.debt_commands import (
    ReopenDebtInputDTO,
    WriteOffDebtInputDTO,
)
from src.modules.debts.application.use_cases.reopen_debt import ReopenDebtUseCase
from src.modules.debts.application.use_cases.write_off_debt import WriteOffDebtUseCase
from src.modules.debts.domain.errors import (
    AlreadyWrittenOffError,
    DebtNotFoundError,
    NotWritableOffError,
    NotWrittenOffError,
)

from .fakes import TODAY, FakeDebtLedger, FakeDebtRepository, debt, new_user_id, settled


def _write_off(debts: FakeDebtRepository, ledger: FakeDebtLedger) -> WriteOffDebtUseCase:
    return WriteOffDebtUseCase(
        debt_repository=debts, settlement_reader=ledger, transfer_recorder=ledger
    )


def _reopen(debts: FakeDebtRepository, ledger: FakeDebtLedger) -> ReopenDebtUseCase:
    return ReopenDebtUseCase(
        debt_repository=debts, settlement_reader=ledger, transfer_recorder=ledger
    )


@pytest.mark.asyncio
async def test_the_loss_is_the_cash_that_never_came_back() -> None:
    user_id = new_user_id()
    lent = debt(user_id=user_id, direction="incoming", amount=100_000)
    ledger = FakeDebtLedger()
    ledger.seed(settled(lent, principal=100_000, instalments=(30_000,)))

    output = await _write_off(FakeDebtRepository([lent]), ledger).execute(
        WriteOffDebtInputDTO(user_id=user_id, debt_id=lent.id, today=TODAY)
    )

    # 100.000 out, 30.000 back: the 70.000 still out there is what was lost.
    losses = [entry for entry in ledger.recorded if entry["is_loss"]]
    assert [entry["amount"] for entry in losses] == [70_000]
    assert output.status == "written_off"
    assert output.remaining == 0


@pytest.mark.asyncio
async def test_the_loss_comes_out_of_the_debt_not_the_account() -> None:
    """The account was debited the day the money was lent. Charging it again would
    say the user paid twice for the same friend."""
    user_id = new_user_id()
    lent = debt(user_id=user_id, direction="incoming", amount=50_000)
    ledger = FakeDebtLedger()
    ledger.seed(settled(lent, principal=50_000))

    await _write_off(FakeDebtRepository([lent]), ledger).execute(
        WriteOffDebtInputDTO(user_id=user_id, debt_id=lent.id, today=TODAY)
    )

    loss = next(entry for entry in ledger.recorded if entry["is_loss"])
    assert loss["debt_id"] == lent.id
    assert "account_id" not in loss


@pytest.mark.asyncio
async def test_a_split_that_moved_no_cash_books_no_expense() -> None:
    """The bill already left as one expense. A second one charges the same dinner
    twice — and this is the case a stored `amount` would have got wrong."""
    user_id = new_user_id()
    share = debt(user_id=user_id, direction="incoming", amount=35_000)
    ledger = FakeDebtLedger()

    output = await _write_off(FakeDebtRepository([share]), ledger).execute(
        WriteOffDebtInputDTO(user_id=user_id, debt_id=share.id, today=TODAY)
    )

    assert ledger.recorded == []
    # It still closes: the user gave up, whether or not it cost them anything today.
    assert output.status == "written_off"


@pytest.mark.asyncio
async def test_a_debt_already_repaid_in_full_costs_nothing_to_give_up() -> None:
    user_id = new_user_id()
    lent = debt(user_id=user_id, direction="incoming", amount=80_000)
    ledger = FakeDebtLedger()
    ledger.seed(settled(lent, principal=80_000, instalments=(80_000,)))

    await _write_off(FakeDebtRepository([lent]), ledger).execute(
        WriteOffDebtInputDTO(user_id=user_id, debt_id=lent.id, today=TODAY)
    )

    assert ledger.recorded == []


@pytest.mark.asyncio
async def test_the_write_off_is_never_counted_as_a_repayment() -> None:
    """It leaves the debt exactly like an instalment does and means the opposite.
    Summing the two would report a friend as having paid what they never paid."""
    user_id = new_user_id()
    lent = debt(user_id=user_id, direction="incoming", amount=100_000)
    ledger = FakeDebtLedger()
    ledger.seed(settled(lent, principal=100_000))

    output = await _write_off(FakeDebtRepository([lent]), ledger).execute(
        WriteOffDebtInputDTO(user_id=user_id, debt_id=lent.id, today=TODAY)
    )

    assert output.paid_total == 0
    assert output.payments == []


@pytest.mark.asyncio
async def test_money_the_user_owes_cannot_be_written_off() -> None:
    """Being forgiven is a windfall, not a loss — a different story with different
    arithmetic, and one this app does not tell yet rather than tells wrong."""
    user_id = new_user_id()
    borrowed = debt(user_id=user_id, direction="outgoing", amount=100_000)
    ledger = FakeDebtLedger()

    with pytest.raises(NotWritableOffError):
        await _write_off(FakeDebtRepository([borrowed]), ledger).execute(
            WriteOffDebtInputDTO(user_id=user_id, debt_id=borrowed.id, today=TODAY)
        )


@pytest.mark.asyncio
async def test_giving_up_twice_is_rejected_not_charged_twice() -> None:
    user_id = new_user_id()
    lost = debt(user_id=user_id, direction="incoming", written_off_on="2026-07-01")
    ledger = FakeDebtLedger()

    with pytest.raises(AlreadyWrittenOffError):
        await _write_off(FakeDebtRepository([lost]), ledger).execute(
            WriteOffDebtInputDTO(user_id=user_id, debt_id=lost.id, today=TODAY)
        )
    assert ledger.recorded == []


@pytest.mark.asyncio
async def test_someone_elses_debt_cannot_be_written_off() -> None:
    ledger = FakeDebtLedger()
    theirs = debt(user_id=new_user_id(), direction="incoming")

    with pytest.raises(DebtNotFoundError):
        await _write_off(FakeDebtRepository([theirs]), ledger).execute(
            WriteOffDebtInputDTO(user_id=new_user_id(), debt_id=theirs.id, today=TODAY)
        )


@pytest.mark.asyncio
async def test_they_paid_after_all_and_the_loss_disappears_with_the_month() -> None:
    user_id = new_user_id()
    lent = debt(user_id=user_id, direction="incoming", amount=100_000)
    ledger = FakeDebtLedger()
    ledger.seed(settled(lent, principal=100_000))
    debts = FakeDebtRepository([lent])

    await _write_off(debts, ledger).execute(
        WriteOffDebtInputDTO(user_id=user_id, debt_id=lent.id, today=TODAY)
    )
    output = await _reopen(debts, ledger).execute(
        ReopenDebtInputDTO(user_id=user_id, debt_id=lent.id, today=TODAY)
    )

    # The expense is deleted, not offset: the month it landed in stops showing a loss
    # that never happened, and the claim comes back at what it stood at.
    assert ledger.reverted == ["loss-1"]
    assert output.written_off_on is None
    assert output.remaining == 100_000
    assert output.status == "pending"


@pytest.mark.asyncio
async def test_reopening_a_live_debt_is_rejected() -> None:
    user_id = new_user_id()
    alive = debt(user_id=user_id, direction="incoming")

    with pytest.raises(NotWrittenOffError):
        await _reopen(FakeDebtRepository([alive]), FakeDebtLedger()).execute(
            ReopenDebtInputDTO(user_id=user_id, debt_id=alive.id, today=TODAY)
        )
