"""What is left of a debt and the state it is in — derived, never stored.

Everything here takes the debt's raw facts (amount, due date) plus **what has actually
been repaid** and the caller's `today`, and answers from them. The prototype persisted
a `balance` and showed due dates as display strings ("21 may"), and both went stale the
moment anything moved; these functions are the fix.

`repaid` is not a field of the debt. It is the sum of the transfers that carried money
back out of it, read through `SettlementReader` — so a repayment and the cash that made
it are the same fact, and deleting the movement in Movimientos undoes both at once.
Passing it in rather than reading it here is what keeps this module pure: the domain
does the arithmetic, the application fetches the numbers.
"""

from typing import Literal

from src.modules.debts.domain.entities.debt import Debt

DebtStatus = Literal["pending", "partial", "paid", "overdue", "written_off"]


def remaining(debt: Debt, repaid: int) -> int:
    """What is still owed.

    Zero once it is written off: giving up is the answer to this question, not a
    footnote to it. Every total in the app filters on this number, so a debt the
    user has abandoned stops being counted the moment they abandon it — without a
    single caller having to remember the case.

    Clamped at zero besides: `add_payment` rejects overpaying, so this should never
    go negative — but it is derived from movements now, and a ledger that reports a
    person owing less than nothing would be worse than one that rounds a bug away.
    """
    if debt.written_off_on is not None:
        return 0
    return max(debt.amount - repaid, 0)


def status(debt: Debt, repaid: int, today: str) -> DebtStatus:
    """`written_off` beats everything, then `paid` — a settled debt cannot be overdue,
    whatever the calendar says. `overdue` needs both a due date in the past **and**
    money still owed. ISO strings compare as dates, so `<` is the whole arithmetic.

    Written off and paid are deliberately different words for the same zero: one was
    collected, the other was lost, and a screen that called them both "PAGADO" would
    be telling the user a friend paid them back when nobody did.
    """
    if debt.written_off_on is not None:
        return "written_off"
    if remaining(debt, repaid) == 0:
        return "paid"
    if debt.due_on is not None and debt.due_on < today:
        return "overdue"
    if repaid > 0:
        return "partial"
    return "pending"
