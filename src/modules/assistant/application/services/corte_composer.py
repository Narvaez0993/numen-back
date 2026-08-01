"""El Corte's composition — pure functions over domain-computed views.

Every number in every slide comes from a reader; the model narrates later and
cannot touch them. The playlist is adaptive: a slide that would say nothing
(no categories, one lonely spending day, no goal) simply doesn't play.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from src.modules.assistant.application.ports.budgets_reader import BudgetsView
from src.modules.assistant.application.ports.goals_reader import GoalView
from src.modules.assistant.application.ports.movements_reader import (
    DaySpendView,
    PeriodSummaryView,
)
from src.modules.assistant.domain.periods import round_to_nice, round_to_nice_down

CORTE_MIN_MOVEMENTS: Final[int] = 3
MAX_BARS: Final[int] = 3
FUN_FACT_MIN_DAYS: Final[int] = 2
CAP_SUGGESTION_FRACTION: Final[float] = 0.9


@dataclass(frozen=True)
class CorteFacts:
    """Everything the composer may look at, frozen. `budgets` was snapshotted at
    the LAST day of the period — the job runs in the next month, and asking
    budgets about "today" would answer about the wrong one."""

    period: str
    summary: PeriodSummaryView
    previous: PeriodSummaryView
    days: tuple[DaySpendView, ...]
    category_names: Mapping[str, str]
    budgets: BudgetsView
    goals: tuple[GoalView, ...]
    tier: str
    category_caps_free_limit: int


@dataclass(frozen=True)
class PlayDraft:
    """A chosen move before it becomes a `Play` (the use case mints the id)."""

    action: str
    params: Mapping[str, Any]


def _expense_count(summary: PeriodSummaryView) -> int:
    return sum(c.count for c in summary.by_category)


def pick_goal(facts: CorteFacts) -> GoalView | None:
    """The month's goal story: the furthest-along pocket still in the game."""
    alive = [g for g in facts.goals if not g.archived]
    if not alive:
        return None
    return max(alive, key=lambda g: g.pct)


def pick_monthly_play(facts: CorteFacts) -> PlayDraft | None:
    """One move, chosen by priority. Create-vs-update is decided HERE: a raise
    carries the budget_id it will update, a set carries what it will create."""
    # Broken = `used >= 1`, NOT `over`: budgets' `over` is where the month is
    # PROJECTED to close, and it is null in the first days — a cap already blown
    # on the 1st would look healthy if we asked the projection.
    broken = [c for c in facts.budgets.categories if c.used >= 1]
    if broken:
        worst = max(broken, key=lambda c: c.used)
        return PlayDraft(
            action="raise_category_cap",
            params={
                "budget_id": worst.id,
                "category_id": worst.category_id,
                "category_name": facts.category_names.get(worst.category_id, "?"),
                "current_target": worst.target,
                "target": round_to_nice(worst.spent),
            },
        )

    capped = {c.category_id for c in facts.budgets.categories}
    has_slot = facts.tier == "plus" or len(capped) < facts.category_caps_free_limit
    uncapped = [
        c
        for c in facts.summary.by_category
        if c.category_id is not None and c.category_id not in capped
    ]
    if uncapped and has_slot:
        biggest = max(uncapped, key=lambda c: c.spent)
        target = round_to_nice_down(int(biggest.spent * CAP_SUGGESTION_FRACTION))
        if target > 0 and biggest.category_id is not None:
            goal = pick_goal(facts)
            return PlayDraft(
                action="set_category_cap",
                params={
                    "category_id": biggest.category_id,
                    "category_name": facts.category_names.get(biggest.category_id, "?"),
                    "target": target,
                    "linked_goal_id": goal.id if goal else None,
                },
            )

    if facts.budgets.month is None and facts.summary.expense_total > 0:
        return PlayDraft(
            action="set_month_cap",
            params={"target": round_to_nice(facts.summary.expense_total)},
        )

    return None


def compose_slides(facts: CorteFacts, play_id: str | None) -> list[dict[str, Any]]:
    """The playlist, in narrative order, without `text` (narración fills it).
    Names are denormalized into the slides on purpose: a deleted category must
    not break July's story in October."""
    slides: list[dict[str, Any]] = [{"type": "cover", "id": "cover"}]

    slides.append(
        {
            "type": "big_number",
            "id": "big_number",
            "amount": facts.summary.expense_total,
            "count": _expense_count(facts.summary),
        }
    )

    categorized = [
        c for c in facts.summary.by_category if c.category_id is not None and c.spent > 0
    ]
    if categorized and facts.summary.expense_total > 0:
        top = sorted(categorized, key=lambda c: c.spent, reverse=True)[:MAX_BARS]
        slides.append(
            {
                "type": "category_bars",
                "id": "category_bars",
                "bars": [
                    {
                        "category_id": c.category_id,
                        "name": facts.category_names.get(c.category_id or "", "?"),
                        "amount": c.spent,
                        "pct": c.spent / facts.summary.expense_total,
                    }
                    for c in top
                ],
            }
        )

    if len(facts.days) >= FUN_FACT_MIN_DAYS:
        heaviest = max(facts.days, key=lambda d: d.spent)
        slides.append(
            {
                "type": "fun_fact",
                "id": "fun_fact",
                "day": heaviest.day,
                "amount": heaviest.spent,
                "count": heaviest.count,
            }
        )

    if facts.previous.count == 0:
        slides.append({"type": "first_month", "id": "first_month"})
    elif facts.previous.expense_total > 0:
        current, previous = facts.summary.expense_total, facts.previous.expense_total
        slides.append(
            {
                "type": "pulse",
                "id": "pulse",
                "current": current,
                "previous": previous,
                "delta_pct": (current - previous) / previous,
            }
        )

    goal = pick_goal(facts)
    if goal is not None:
        slides.append(
            {
                "type": "goal",
                "id": "goal",
                "goal_id": goal.id,
                "name": goal.name,
                "saved": goal.saved,
                "target": goal.target,
                "pct": goal.pct,
                "needed_per_month": goal.needed_per_month,
            }
        )

    if play_id is not None:
        slides.append({"type": "play", "id": "play", "play_id": play_id})

    return slides
