from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.budgets.application.ports.spend_reader import (
    CategorySpendView,
    MerchantSpendView,
)
from src.modules.budgets.domain.entities.budget import Budget, Scope

FIXED_NOW = datetime(2026, 7, 26, 12, 0, 0, tzinfo=UTC)
TODAY = "2026-07-26"
CURRENCY = "COP"
# 26 July 2026 -> 26 days elapsed, 6 left (the 26th through the 31st).
DAYS_LEFT = 6
DAYS_ELAPSED = 26
TOTAL_DAYS = 31


class FakeBudgetRepository:
    """Enforces the unique `(user, scope, category)` the index enforces, so a test that
    passes here cannot pass only because the store was lenient."""

    def __init__(self, budgets: list[Budget] | None = None) -> None:
        self.budgets = list(budgets or [])

    async def list_by_user(self, user_id: UUID) -> list[Budget]:
        return [b for b in self.budgets if b.user_id == user_id]

    async def find(self, user_id: UUID, budget_id: str) -> Budget | None:
        for budget in self.budgets:
            if budget.id == budget_id and budget.user_id == user_id:
                return budget
        return None

    async def find_global(self, user_id: UUID) -> Budget | None:
        for budget in self.budgets:
            if budget.user_id == user_id and budget.scope == "global":
                return budget
        return None

    async def find_for_category(self, user_id: UUID, category_id: str) -> Budget | None:
        for budget in self.budgets:
            if (
                budget.user_id == user_id
                and budget.scope == "category"
                and budget.category_id == category_id
            ):
                return budget
        return None

    async def save(self, budget: Budget) -> None:
        for index, existing in enumerate(self.budgets):
            if existing.id == budget.id:
                self.budgets[index] = budget
                return
        clash = [
            b
            for b in self.budgets
            if b.user_id == budget.user_id
            and b.scope == budget.scope
            and b.category_id == budget.category_id
        ]
        if clash:
            raise AssertionError("the unique index would have rejected this insert")
        self.budgets.append(budget)

    async def delete(self, user_id: UUID, budget_id: str) -> None:
        self.budgets = [b for b in self.budgets if not (b.id == budget_id and b.user_id == user_id)]


class FakeSpendReader:
    """Answers with fixed spending per category; `spent` is their sum, exactly as the
    real aggregation over the same range would be."""

    def __init__(
        self,
        *,
        by_category: list[CategorySpendView] | None = None,
        merchants: dict[str | None, list[MerchantSpendView]] | None = None,
    ) -> None:
        self.rows = list(by_category or [])
        self.merchants = merchants or {}
        self.ranges: list[tuple[str, str]] = []

    async def spent(self, user_id: UUID, date_from: str, date_to: str) -> int:
        self.ranges.append((date_from, date_to))
        return sum(row.spent for row in self.rows)

    async def by_category(
        self, user_id: UUID, date_from: str, date_to: str
    ) -> list[CategorySpendView]:
        self.ranges.append((date_from, date_to))
        return list(self.rows)

    async def top_merchants(
        self,
        user_id: UUID,
        date_from: str,
        date_to: str,
        category_id: str | None,
        limit: int,
    ) -> list[MerchantSpendView]:
        return self.merchants.get(category_id, [])[:limit]


class FakeCategoryReader:
    def __init__(self, known: list[str] | None = None) -> None:
        self.known = known if known is not None else ["mercado", "domicilios", "transporte"]

    async def exists(self, user_id: UUID, category_id: str) -> bool:
        return category_id in self.known


def budget(
    *,
    user_id: UUID,
    scope: Scope = "global",
    category_id: str | None = None,
    target: int = 3_000_000,
    since: str = "2026-07",
) -> Budget:
    return Budget(
        id=str(uuid4()),
        user_id=user_id,
        scope=scope,
        category_id=category_id,
        target=target,
        since=since,
        created_at=FIXED_NOW,
    )


def spend(category_id: str | None, amount: int, count: int = 1) -> CategorySpendView:
    return CategorySpendView(category_id=category_id, spent=amount, count=count)


def merchant(label: str, amount: int, count: int = 1) -> MerchantSpendView:
    return MerchantSpendView(label=label, spent=amount, count=count)


def new_user_id() -> UUID:
    return uuid4()
