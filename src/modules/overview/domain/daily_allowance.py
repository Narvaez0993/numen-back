from dataclasses import dataclass
from typing import Literal

AllowanceBasis = Literal["budget", "income", "none"]


@dataclass(frozen=True)
class DailyAllowance:
    """How much is left to spend today, and **on what that answer is based**.

    The ladder, most authoritative first:

    | basis      | when                        | available                          |
    |------------|-----------------------------|------------------------------------|
    | `budget`   | there is a monthly budget   | (budget - spent) / days left       |
    | `income`   | income was registered       | (income - spent) / days left       |
    | `none`     | neither                     | 0 — the client shows the month     |

    `basis` travels in the payload on purpose: the client must be able to say
    *where the number comes from* instead of presenting an invented cap as advice.
    `budget` is reserved for phase 3 — adding budgets will not change this shape.

    `available` may be **negative** when the user already went past their income;
    that is the honest answer and the copy says so, instead of showing a zero.
    """

    available: int
    basis: AllowanceBasis

    @classmethod
    def none(cls) -> "DailyAllowance":
        return cls(available=0, basis="none")


def compute(
    *,
    spent: int,
    income: int,
    days_left: int,
    budget: int | None = None,
) -> DailyAllowance:
    """The ladder as a pure function — the hero's rule, testable on its own."""
    if days_left <= 0:
        return DailyAllowance.none()

    if budget is not None and budget > 0:
        return DailyAllowance(available=(budget - spent) // days_left, basis="budget")

    if income > 0:
        return DailyAllowance(available=(income - spent) // days_left, basis="income")

    # Nothing to divide: without income or a budget there is no honest daily figure.
    return DailyAllowance.none()
