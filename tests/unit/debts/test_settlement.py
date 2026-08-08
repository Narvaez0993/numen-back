"""Reading a debt's transfers against the direction it runs.

This is the subtle half of the move to real money, and the one a future refactor is
most likely to get backwards: the SAME movement means opposite things on either side
of the deal. Money leaving my account into a debt is a loan when they owe me, and an
instalment when I owe them. Nothing about the movement says which — only the debt does.
"""

from src.modules.debts.application.ports.settlement_reader import (
    NO_SETTLEMENT,
    DebtMovement,
    DebtSettlement,
)
from src.modules.debts.application.services import settlement as settlement_service

from .fakes import debt, new_user_id, settled


def test_when_they_owe_me_the_instalment_is_the_money_coming_back() -> None:
    lent = debt(user_id=new_user_id(), direction="incoming", amount=100_000)

    history = settled(lent, principal=100_000, instalments=(30_000, 20_000))

    # The principal left my account INTO the debt; it is not a repayment of itself.
    assert settlement_service.repaid(lent, history) == 50_000


def test_when_i_owe_the_instalment_is_the_money_going_out() -> None:
    borrowed = debt(user_id=new_user_id(), direction="outgoing", amount=100_000)

    history = settled(borrowed, principal=100_000, instalments=(40_000,))

    # Here the principal ARRIVED in my account, and my payment is what leaves.
    assert settlement_service.repaid(borrowed, history) == 40_000


def test_the_same_transfer_reads_opposite_on_each_side() -> None:
    """The property the whole module hangs on, stated once."""
    into_the_debt = DebtSettlement(
        debt_id="d1",
        into_debt=(
            DebtMovement(
                movement_id="m1", amount=10_000, occurred_on="2026-07-27", description="x"
            ),
        ),
        out_of_debt=(),
    )

    they_owe_me = debt(user_id=new_user_id(), direction="incoming")
    i_owe_them = debt(user_id=new_user_id(), direction="outgoing")

    # Money leaving my account: a loan when they owe me, my instalment when I owe.
    assert settlement_service.repaid(they_owe_me, into_the_debt) == 0
    assert settlement_service.repaid(i_owe_them, into_the_debt) == 10_000


def test_a_debt_that_never_moved_cash_reports_nothing_owed_back() -> None:
    """A dinner split: the bill already left as one expense, so no transfer exists."""
    share = debt(user_id=new_user_id(), direction="incoming", amount=35_000)

    assert settlement_service.repaid(share, NO_SETTLEMENT) == 0
    assert settlement_service.instalments(share, NO_SETTLEMENT) == ()


def test_instalments_come_back_as_the_movements_that_carried_them() -> None:
    lent = debt(user_id=new_user_id(), direction="incoming")

    paid = settlement_service.instalments(lent, settled(lent, instalments=(5_000, 7_000)))

    assert [p.amount for p in paid] == [5_000, 7_000]
    # The id is the movement's: the user can open the instalment in Movimientos.
    assert [p.movement_id for p in paid] == ["mov-0", "mov-1"]


def test_a_write_off_leaves_the_debt_without_being_a_repayment() -> None:
    """The subtlest confusion in the module: the loss travels out of the claim just
    like an instalment, and means the opposite. Summed together they would report a
    friend as having paid what they never paid."""
    lent = debt(user_id=new_user_id(), direction="incoming", amount=100_000)
    history = DebtSettlement(
        debt_id=lent.id,
        into_debt=(
            DebtMovement(
                movement_id="principal",
                amount=100_000,
                occurred_on="2026-07-01",
                description="Préstamo",
            ),
        ),
        out_of_debt=(
            DebtMovement(
                movement_id="abono",
                amount=30_000,
                occurred_on="2026-07-20",
                description="Abono",
            ),
            DebtMovement(
                movement_id="perdida",
                amount=70_000,
                occurred_on="2026-07-27",
                description="Deuda dada por perdida",
                is_loss=True,
            ),
        ),
    )

    assert settlement_service.repaid(lent, history) == 30_000
    assert settlement_service.principal(lent, history) == 100_000
    assert [loss.movement_id for loss in settlement_service.losses(history)] == ["perdida"]


def test_the_principal_of_a_split_is_nothing_because_no_cash_crossed() -> None:
    """The number that stops a written-off dinner from being charged twice."""
    share = debt(user_id=new_user_id(), direction="incoming", amount=35_000)

    assert settlement_service.principal(share, NO_SETTLEMENT) == 0
