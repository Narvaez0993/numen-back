"""The weekly review's composition — pure functions over domain-computed views.

The coach's promise: real value, not vibes. A rough week points at a concrete
fix (raise the cap that broke); a good week earns a domain-verified treat.
Every play the previous review proposed comes back with its CURRENT state —
accountability the user can check against real objects.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Final

from src.modules.assistant.application.ports.budgets_reader import BudgetsView
from src.modules.assistant.application.ports.goals_reader import GoalView
from src.modules.assistant.application.ports.movements_reader import PeriodSummaryView
from src.modules.assistant.application.services.corte_composer import PlayDraft
from src.modules.assistant.domain.entities.agent_output import Play
from src.modules.assistant.domain.periods import round_to_nice, round_to_nice_down
from src.modules.assistant.domain.slack import monthly_slack

WEEKLY_MIN_MOVEMENTS: Final[int] = 3
CAP_NEAR_USED: Final[float] = 0.8
NEAR_CAP_RAISE_FACTOR: Final[float] = 1.25
TREAT_FRACTION_OF_SLACK: Final[float] = 0.2


@dataclass(frozen=True)
class WeeklyFacts:
    """Everything the weekly coach may look at, frozen at composition time."""

    period: str
    week: PeriodSummaryView
    previous_week: PeriodSummaryView
    month_to_date: PeriodSummaryView
    pending_charges: int
    """Charges still queued this month (pending/scheduled only — settled money
    already lives inside `month_to_date.expense_total`, never count it twice)."""
    category_names: Mapping[str, str]
    budgets: BudgetsView
    goals: tuple[GoalView, ...]
    treat_slack_fraction: float
    previous_plays: tuple[Play, ...] = field(default_factory=tuple)
    """Last week's proposals with their CURRENT states — the accountability."""


@dataclass(frozen=True)
class WeeklyComposition:
    week_total: int
    prev_week_total: int | None
    delta_pct: float | None
    top_category_id: str | None
    top_category_name: str | None
    plays: tuple[PlayDraft, ...]
    accountability: tuple[dict[str, Any], ...]


def _diagnosis_numbers(facts: WeeklyFacts) -> tuple[int, int | None, float | None]:
    week_total = facts.week.expense_total
    if facts.previous_week.count == 0:
        return week_total, None, None
    previous = facts.previous_week.expense_total
    delta = (week_total - previous) / previous if previous > 0 else None
    return week_total, previous, delta


def _top_category(facts: WeeklyFacts) -> tuple[str | None, str | None]:
    spends = {c.category_id: c.spent for c in facts.week.by_category if c.category_id}
    if not spends:
        return None, None
    top_id = max(spends, key=lambda cid: spends[cid])
    return top_id, facts.category_names.get(top_id, "?")


def _cap_play(facts: WeeklyFacts) -> PlayDraft | None:
    """The fix for the week's budget trouble: the most-broken cap first, then
    the one burning past 80% — raised to a number that can actually hold."""
    troubled = [c for c in facts.budgets.categories if c.used >= CAP_NEAR_USED]
    if not troubled:
        return None
    worst = max(troubled, key=lambda c: c.used)
    # `used >= 1` is the fact; budgets' `over` is a projection that stays null in
    # the first days of the month, so asking it would call a blown cap healthy.
    broken = worst.used >= 1
    target = (
        round_to_nice(worst.spent)
        if broken
        else round_to_nice(int(worst.target * NEAR_CAP_RAISE_FACTOR))
    )
    return PlayDraft(
        action="raise_category_cap",
        params={
            "budget_id": worst.id,
            "category_id": worst.category_id,
            "category_name": facts.category_names.get(worst.category_id, "?"),
            "current_target": worst.target,
            "target": target,
        },
    )


def pick_weekly_plays(facts: WeeklyFacts) -> tuple[PlayDraft, ...]:
    """0-3 moves, by priority. The treat NEVER shares a review with a cap fix:
    "you broke a budget, treat yourself" is not coaching."""
    plays: list[PlayDraft] = []

    cap_fix = _cap_play(facts)
    if cap_fix:
        plays.append(cap_fix)

    income = facts.month_to_date.income_total
    expense = facts.month_to_date.expense_total
    slack_base = monthly_slack(income, expense, facts.pending_charges, None)

    goal = pick_goal_with_pace(facts.goals)
    if goal is not None and goal.needed_per_month is not None and slack_base > 0:
        amount = round_to_nice_down(min(goal.needed_per_month, slack_base))
        if amount > 0:
            plays.append(
                PlayDraft(
                    action="contribute_goal",
                    params={"goal_id": goal.id, "goal_name": goal.name, "amount": amount},
                )
            )

    goal_needed = goal.needed_per_month if goal is not None else None
    slack_after_goal = monthly_slack(income, expense, facts.pending_charges, goal_needed)
    if cap_fix is None and income > 0 and slack_after_goal > facts.treat_slack_fraction * income:
        treat = round_to_nice_down(int(slack_after_goal * TREAT_FRACTION_OF_SLACK))
        if treat > 0:
            plays.append(PlayDraft(action="treat", params={"amount": treat}))

    return tuple(plays)


def pick_goal_with_pace(goals: tuple[GoalView, ...]) -> GoalView | None:
    """The goal worth pacing: alive, unfinished, furthest along."""
    alive = [g for g in goals if not g.archived and not g.achieved]
    return max(alive, key=lambda g: g.pct) if alive else None


def compose_weekly(facts: WeeklyFacts) -> WeeklyComposition:
    week_total, prev_total, delta = _diagnosis_numbers(facts)
    top_id, top_name = _top_category(facts)
    accountability = tuple(
        {
            "play_id": play.id,
            "action": play.action,
            "text": play.text,
            "status": play.status,
        }
        for play in facts.previous_plays
    )
    return WeeklyComposition(
        week_total=week_total,
        prev_week_total=prev_total,
        delta_pct=delta,
        top_category_id=top_id,
        top_category_name=top_name,
        plays=pick_weekly_plays(facts),
        accountability=accountability,
    )
