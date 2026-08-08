"""Reading a debt's cash flows against the direction it runs.

The reader reports which way the money went and stops there, because the same
direction means opposite things on either side of the deal:

| debt direction        | money INTO the debt | money OUT of the debt |
|-----------------------|---------------------|-----------------------|
| `incoming` (they owe) | the loan I made     | their instalment      |
| `outgoing` (I owe)    | my instalment       | the money I received  |

So "who is paying whom" is not a property of the movement — it is the movement read
against the agreement. This module is the one place that reads it, so no caller has
to remember the table.

The write-off is the exception that proves it: it leaves the debt like a repayment
and means the opposite, so it is separated by `is_loss` before the table is ever
consulted. Nobody paid; the claim was given up.
"""

from src.modules.debts.application.ports.settlement_reader import (
    DebtMovement,
    DebtSettlement,
)
from src.modules.debts.domain.entities.debt import Debt


def instalments(debt: Debt, settlement: DebtSettlement) -> tuple[DebtMovement, ...]:
    """The transfers that paid this debt down, oldest first."""
    if debt.direction == "incoming":
        # They owe me: their money comes out of the claim and into my account.
        return tuple(paid for paid in settlement.out_of_debt if not paid.is_loss)
    return settlement.into_debt


def repaid(debt: Debt, settlement: DebtSettlement) -> int:
    """How much of it has been paid off. The number `status.py` needs."""
    return sum(instalment.amount for instalment in instalments(debt, settlement))


def principal(debt: Debt, settlement: DebtSettlement) -> int:
    """The cash that actually crossed when the deal was struck.

    Not the same as `debt.amount`: a dinner split owes real money and moved none —
    the bill already left as one expense. Writing that off must book no second
    expense, and this is the number that says so.
    """
    if debt.direction == "incoming":
        return sum(lent.amount for lent in settlement.into_debt)
    return sum(borrowed.amount for borrowed in settlement.out_of_debt if not borrowed.is_loss)


def losses(settlement: DebtSettlement) -> tuple[DebtMovement, ...]:
    """The write-off expenses booked against this debt.

    Direction plays no part: a claim given up is a loss on either side of the table,
    and there is at most one — but reading it as a list is what lets `reopen` find
    the movement to delete without storing its id anywhere.
    """
    return tuple(movement for movement in settlement.out_of_debt if movement.is_loss)
