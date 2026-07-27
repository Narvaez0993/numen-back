from pydantic import BaseModel, Field

# Targets are integers in the minor unit of the user's currency, which the server owns:
# no request body carries a currency.


class CreateBudgetRequest(BaseModel):
    scope: str
    """`global` for the month's ceiling, `category` for a watch on one category."""
    category_id: str | None = None
    target: int = Field(gt=0)


class UpdateBudgetRequest(BaseModel):
    """Only the number. Moving a cap to another category is a delete plus a create."""

    target: int = Field(gt=0)


class BudgetResponse(BaseModel):
    id: str
    scope: str
    category_id: str | None
    target: int
    since: str
    """`YYYY-MM` — the month this value was set in. The cap itself is standing: it
    applies to every month from then on until the user changes it."""


class CapResponse(BaseModel):
    """A cap and the month measured against it. Every field is derived."""

    id: str
    target: int
    spent: int
    remaining: int
    """Negative once the user is over the cap — reported, not clamped to zero."""
    used: float
    """`spent / target`, uncapped: `1.4` is 140%."""
    per_day: int | None
    """What is left divided by the days that are left, **today included**: the answer
    to "how much for today and the rest". `null` once the cap is spent."""
    projected: int | None
    """Where the month closes at the current rate; `null` in its first days."""
    over: int | None
    """How much past the cap it would close; `null` when it closes inside."""


class MerchantResponse(BaseModel):
    label: str
    spent: int
    count: int


class CategoryCapResponse(CapResponse):
    category_id: str
    count: int
    top_merchants: list[MerchantResponse]


class BudgetsSnapshotResponse(BaseModel):
    currency: str
    period: str
    days_left: int
    days_elapsed: int
    month: CapResponse | None
    """The global ceiling; `null` when the user has not set one."""
    categories: list[CategoryCapResponse]
    """Only the categories the user chose to watch, most urgent first. **Not additive
    with `month`**: every expense counts against the ceiling regardless."""
