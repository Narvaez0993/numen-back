"""What is left of a debt and the state it is in — derived, never stored.

Everything here takes the debt's raw facts (amount, payments, due date) plus the
caller's `today` and answers from them. The prototype persisted a `balance` and showed
due dates as display strings ("21 may"), and both went stale the moment anything moved;
these functions are the fix, and the client's own copies die in favour of the payload.
"""

from typing import Literal

from src.modules.debts.domain.entities.debt import Debt

DebtStatus = Literal["pending", "partial", "paid", "overdue"]


def paid_total(debt: Debt) -> int:
    return sum(payment.amount for payment in debt.payments)


def remaining(debt: Debt) -> int:
    """Never negative: `add_payment` rejects overpaying, so the ledger cannot say a
    person owes less than nothing."""
    return debt.amount - paid_total(debt)


def status(debt: Debt, today: str) -> DebtStatus:
    """`paid` wins over everything — a settled debt cannot be overdue, whatever the
    calendar says. `overdue` needs both a due date in the past **and** money still
    owed. ISO strings compare as dates, so `<` is the whole date arithmetic."""
    if remaining(debt) == 0:
        return "paid"
    if debt.due_on is not None and debt.due_on < today:
        return "overdue"
    if paid_total(debt) > 0:
        return "partial"
    return "pending"
