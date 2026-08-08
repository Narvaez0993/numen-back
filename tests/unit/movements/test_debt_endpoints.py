"""A debt as a movement endpoint: transfers, plus the one expense that ends it.

A claim on someone else holds money aside, like a pocket does — so lending travels as
a transfer and the month's expenses do not move. Unlike a pocket, a claim can be lost,
and that loss is a real expense: the `expense` out of a debt is the write-off, and the
only shape asymmetry between the two.

Out of the DEBT, never out of an account — that one was already debited the day the
money was lent. The HTTP schemas refuse `debt` refs outright (only the debts module
mints them, through its port), so these tests pin the domain layer behind that.
"""

import pytest

from src.modules.movements.domain.entities.movement import SourceRef
from src.modules.movements.domain.errors import InvalidMovementError
from src.modules.movements.domain.validation import ensure_shape

ACCOUNT = SourceRef(type="account", id="nequi")
CARD = SourceRef(type="credit_card", id="visa")
CLAIM = SourceRef(type="debt", id="andres")
OTHER_CLAIM = SourceRef(type="debt", id="sofia")
POCKET = SourceRef(type="goal", id="viaje")


def test_lending_is_a_transfer_out_of_an_account() -> None:
    ensure_shape("transfer", ACCOUNT, CLAIM, None)


def test_a_repayment_is_the_same_transfer_backwards() -> None:
    ensure_shape("transfer", CLAIM, ACCOUNT, None)


def test_money_never_hops_claim_to_claim() -> None:
    with pytest.raises(InvalidMovementError):
        ensure_shape("transfer", CLAIM, OTHER_CLAIM, None)


def test_a_claim_and_a_pocket_are_not_two_ends_of_a_move() -> None:
    """Neither holds cash, so there is no honest balance to debit."""
    with pytest.raises(InvalidMovementError):
        ensure_shape("transfer", POCKET, CLAIM, None)


def test_the_write_off_is_an_expense_out_of_the_claim() -> None:
    ensure_shape("expense", CLAIM, None, None)


def test_a_pocket_has_no_such_moment() -> None:
    """You cannot lose a pocket of your own money — the exception is the debt's
    alone, and widening it to every held-aside source would let a user 'spend' from
    a goal, which is exactly what the rule exists to stop."""
    with pytest.raises(InvalidMovementError):
        ensure_shape("expense", POCKET, None, None)


def test_income_never_lands_on_a_claim() -> None:
    """Being repaid is the transfer above. Income on a debt would mean the claim
    itself earned money, which nothing in the app can produce."""
    with pytest.raises(InvalidMovementError):
        ensure_shape("income", CLAIM, None, None)


def test_the_write_off_takes_no_destination() -> None:
    with pytest.raises(InvalidMovementError):
        ensure_shape("expense", CLAIM, ACCOUNT, None)


def test_a_card_can_be_the_other_end_of_a_loan() -> None:
    """The domain allows it — a cash advance is a real, if expensive, way to lend.
    The UI does not offer it; that is a product decision, not a ledger rule."""
    ensure_shape("transfer", CARD, CLAIM, None)
