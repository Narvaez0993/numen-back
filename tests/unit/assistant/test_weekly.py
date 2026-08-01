"""The weekly coach: honest slack math, prioritized plays, accountability."""

from datetime import UTC, datetime
from uuid import UUID

from src.modules.assistant.application.ports.budgets_reader import (
    BudgetsView,
    CategoryCapView,
)
from src.modules.assistant.application.ports.goals_reader import GoalView
from src.modules.assistant.application.ports.movements_reader import (
    CategorySpendView,
    DaySpendView,
    PeriodSummaryView,
)
from src.modules.assistant.application.ports.subscriptions_reader import UpcomingChargeView
from src.modules.assistant.application.ports.users_reader import UserView
from src.modules.assistant.application.services.weekly_composer import (
    WeeklyFacts,
    compose_weekly,
    pick_weekly_plays,
)
from src.modules.assistant.application.use_cases.compose_weekly_review import (
    ComposeWeeklyReviewUseCase,
)
from src.modules.assistant.application.use_cases.run_weekly_reviews import (
    RunWeeklyReviewsUseCase,
)
from src.modules.assistant.domain.entities.agent_output import WEEKLY_REVIEW
from src.modules.assistant.domain.slack import monthly_slack
from tests.unit.assistant.fakes import (
    PRICING,
    USER_ID,
    FakeActionLog,
    FakeAgentModel,
    FakeAgentOutputRepository,
    FakeCategoriesReader,
    agent_output,
    play,
    turn,
)

PERIOD = "2026-W31"  # Jul 27 - Aug 2; reviewed on Monday Aug 3
NOW = datetime(2026, 8, 3, 7, 0, 0, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


def span(date_from: str, date_to: str, **overrides: object) -> PeriodSummaryView:
    base: dict[str, object] = {
        "date_from": date_from,
        "date_to": date_to,
        "expense_total": 380_000,
        "income_total": 0,
        "count": 8,
        "by_category": (),
    }
    base.update(overrides)
    return PeriodSummaryView(**base)  # type: ignore[arg-type]


def cap(cid: str, target: int, spent: int, *, bid: str = "b-1") -> CategoryCapView:
    over = spent - target if spent > target else None
    return CategoryCapView(
        id=bid,
        category_id=cid,
        target=target,
        spent=spent,
        remaining=target - spent,
        over=over,
        used=spent / target,
    )


def goal(needed: int | None = 400_000, pct: float = 0.6) -> GoalView:
    return GoalView(
        id="g-1",
        name="Viaje",
        target=5_000_000,
        saved=int(5_000_000 * pct),
        pct=pct,
        achieved=False,
        archived=False,
        target_date="2026-12-31",
        projected_on=None,
        needed_per_month=needed,
    )


def facts(**overrides: object) -> WeeklyFacts:
    base: dict[str, object] = {
        "period": PERIOD,
        "week": span(
            "2026-07-27",
            "2026-08-02",
            by_category=(
                CategorySpendView(category_id="comida", spent=220_000, count=5),
                CategorySpendView(category_id=None, spent=40_000, count=1),
            ),
        ),
        "previous_week": span("2026-07-20", "2026-07-26", expense_total=500_000, count=9),
        "month_to_date": span(
            "2026-08-01", "2026-08-03", expense_total=200_000, income_total=4_000_000
        ),
        "pending_charges": 300_000,
        "category_names": {"comida": "Comida"},
        "budgets": BudgetsView(period="2026-08", days_left=28, month=None, categories=()),
        "goals": (goal(),),
        "treat_slack_fraction": 0.10,
        "previous_plays": (),
    }
    base.update(overrides)
    return WeeklyFacts(**base)  # type: ignore[arg-type]


# --- slack: the domain's "does it fit" ---


def test_slack_subtracts_everything_and_can_go_negative() -> None:
    assert monthly_slack(4_000_000, 1_500_000, 300_000, 400_000) == 1_800_000
    assert monthly_slack(0, 100_000, 0, None) == -100_000


# --- the composition ---


def test_diagnosis_compares_weeks_and_names_the_top_category() -> None:
    result = compose_weekly(facts())
    assert result.week_total == 380_000
    assert result.prev_week_total == 500_000
    assert result.delta_pct == (380_000 - 500_000) / 500_000
    assert result.top_category_name == "Comida"


def test_first_tracked_week_has_no_comparison() -> None:
    result = compose_weekly(facts(previous_week=span("2026-07-20", "2026-07-26", count=0)))
    assert result.prev_week_total is None
    assert result.delta_pct is None


def test_accountability_echoes_last_weeks_plays_with_current_states() -> None:
    applied = play(status="applied", text="Techo para Comida")
    result = compose_weekly(facts(previous_plays=(applied,)))
    assert result.accountability == (
        {
            "play_id": "play-1",
            "action": "set_category_cap",
            "text": "Techo para Comida",
            "status": "applied",
        },
    )


# --- the plays, by priority ---


def test_broken_cap_beats_everything_and_kills_the_treat() -> None:
    troubled = facts(
        budgets=BudgetsView(
            period="2026-08",
            days_left=28,
            month=None,
            categories=(cap("comida", 300_000, 470_000, bid="b-c"),),
        ),
        goals=(),
    )
    plays = pick_weekly_plays(troubled)
    assert [p.action for p in plays] == ["raise_category_cap"]
    assert plays[0].params["target"] == 470_000  # round_to_nice of spent


def test_a_blown_cap_without_a_projection_still_counts_as_broken() -> None:
    # `over` is budgets' projection (null early in the month); `used` is the fact.
    blown = CategoryCapView(
        id="b-c",
        category_id="comida",
        target=300_000,
        spent=420_000,
        remaining=-120_000,
        over=None,
        used=1.4,
    )
    plays = pick_weekly_plays(
        facts(
            budgets=BudgetsView(period="2026-08", days_left=28, month=None, categories=(blown,)),
            goals=(),
        )
    )
    assert [p.action for p in plays] == ["raise_category_cap"]
    assert plays[0].params["target"] == 420_000  # the real spend, not target x 1.25


def test_a_cap_past_80_percent_gets_headroom() -> None:
    near = facts(
        budgets=BudgetsView(
            period="2026-08",
            days_left=28,
            month=None,
            categories=(cap("comida", 400_000, 340_000, bid="b-c"),),
        ),
        goals=(),
    )
    plays = pick_weekly_plays(near)
    assert plays[0].action == "raise_category_cap"
    assert plays[0].params["target"] == 500_000  # 400k x 1.25


def test_goal_contribution_fits_inside_the_slack() -> None:
    tight = facts(
        month_to_date=span(
            "2026-08-01", "2026-08-03", expense_total=3_500_000, income_total=4_000_000
        ),
        pending_charges=200_000,
    )
    plays = pick_weekly_plays(tight)
    contribute = next(p for p in plays if p.action == "contribute_goal")
    # slack = 4M - 3.5M - 200k = 300k < needed 400k → capped by the slack.
    assert contribute.params["amount"] == 300_000


def test_treat_needs_a_clean_week_and_real_slack() -> None:
    plays = pick_weekly_plays(facts())
    treat = next(p for p in plays if p.action == "treat")
    # slack after goal = 4M - 200k - 300k - 400k = 3.1M; treat = 20% rounded down.
    assert treat.params["amount"] == 620_000

    no_income = pick_weekly_plays(
        facts(month_to_date=span("2026-08-01", "2026-08-03", income_total=0))
    )
    assert all(p.action != "treat" for p in no_income)


# --- the compose use case ---


def user(uid: UUID = USER_ID, tier: str = "free") -> UserView:
    return UserView(user_id=uid, tier=tier, language="es", currency="COP", objective=None)


class StubMovementsReader:
    def __init__(self, by_span: dict[tuple[str, str], PeriodSummaryView]) -> None:
        self.by_span = by_span

    async def summary(self, user_id: UUID, date_from: str, date_to: str) -> PeriodSummaryView:
        return self.by_span.get(
            (date_from, date_to), span(date_from, date_to, expense_total=0, count=0)
        )

    async def spend_by_day(
        self, user_id: UUID, date_from: str, date_to: str
    ) -> tuple[DaySpendView, ...]:
        return ()


class StubBudgetsReader:
    async def snapshot(self, user_id: UUID, currency: str, today: str) -> BudgetsView:
        return BudgetsView(period=today[:7], days_left=28, month=None, categories=())


class StubGoalsReader:
    async def snapshot(self, user_id: UUID, currency: str, today: str) -> tuple[GoalView, ...]:
        return (goal(),)


class StubSubscriptionsReader:
    async def upcoming_charges(
        self, user_id: UUID, currency: str, date_from: str, date_to: str, limit: int = 10
    ) -> tuple[UpcomingChargeView, ...]:
        return ()


def scripted_model() -> FakeAgentModel:
    def scripted(messages):
        import json

        request = json.loads(messages[-1].text)
        from src.modules.assistant.application.ports.agent_model import ToolCall

        return turn(
            tool_calls=(
                ToolCall(
                    id="c-1",
                    name="narrate",
                    arguments={
                        "items": [
                            {"item_id": i["item_id"], "text": f"Línea de {i['item_id']}."}
                            for i in request["items"]
                        ]
                    },
                ),
            )
        )

    return FakeAgentModel([scripted])


def build_compose(
    outputs: FakeAgentOutputRepository,
    movements: StubMovementsReader,
    model: FakeAgentModel | None = None,
) -> ComposeWeeklyReviewUseCase:
    return ComposeWeeklyReviewUseCase(
        outputs=outputs,
        movements_reader=movements,  # type: ignore[arg-type]
        budgets_reader=StubBudgetsReader(),
        goals_reader=StubGoalsReader(),
        categories_reader=FakeCategoriesReader(),
        subscriptions_reader=StubSubscriptionsReader(),
        agent_model=model or scripted_model(),
        action_log=FakeActionLog(),
        clock=FixedClock(),
        pricing=PRICING,
        model_name="claude-sonnet-5",
        treat_slack_fraction=0.10,
    )


def rich_spans() -> dict[tuple[str, str], PeriodSummaryView]:
    return {
        ("2026-07-27", "2026-08-02"): span(
            "2026-07-27",
            "2026-08-02",
            by_category=(CategorySpendView(category_id="comida", spent=220_000, count=5),),
        ),
        ("2026-07-20", "2026-07-26"): span(
            "2026-07-20", "2026-07-26", expense_total=500_000, count=9
        ),
        ("2026-08-01", "2026-08-03"): span(
            "2026-08-01", "2026-08-03", expense_total=200_000, income_total=4_000_000
        ),
    }


async def test_weekly_review_lands_with_diagnosis_plays_and_accountability() -> None:
    outputs = FakeAgentOutputRepository()
    previous = agent_output(
        kind=WEEKLY_REVIEW,
        period="2026-W30",
        payload={"diagnosis_text": "x"},
        plays=(play(status="applied"),),
    )
    await outputs.add(previous)
    use_case = build_compose(outputs, StubMovementsReader(rich_spans()))

    output_id = await use_case.execute(user(), PERIOD)

    assert output_id is not None
    stored = outputs.outputs[output_id]
    assert stored.kind == WEEKLY_REVIEW
    assert stored.payload["diagnosis_text"] == "Línea de diagnosis."
    assert stored.payload["week_total"] == 380_000
    assert stored.payload["accountability"] == [
        {
            "play_id": "play-1",
            "action": "set_category_cap",
            "text": play().text,
            "status": "applied",
        }
    ]
    actions = [p.action for p in stored.plays]
    assert "contribute_goal" in actions
    assert "treat" in actions  # clean week, real slack


async def test_thin_weeks_skip_without_touching_the_model() -> None:
    outputs = FakeAgentOutputRepository()
    model = FakeAgentModel([])
    thin = {
        ("2026-07-27", "2026-08-02"): span("2026-07-27", "2026-08-02", count=2),
    }
    use_case = build_compose(outputs, StubMovementsReader(thin), model)

    assert await use_case.execute(user(), PERIOD) is None
    assert outputs.outputs == {}
    assert model.requests == []


# --- the sweep and its audience ---


class FakeUsersReader:
    def __init__(self, *users: UserView) -> None:
        self.users = users
        self.asked_tier: list[str | None] = []

    async def list_users(self, tier: str | None = None) -> tuple[UserView, ...]:
        self.asked_tier.append(tier)
        return tuple(u for u in self.users if tier is None or u.tier == tier)


class ScriptedCompose:
    def __init__(self) -> None:
        self.seen: list[UUID] = []

    async def execute(self, target: UserView, period: str) -> str | None:
        self.seen.append(target.user_id)
        return "out-1"


async def test_audience_all_sweeps_everyone_and_plus_filters() -> None:
    free = user(UUID("00000000-0000-0000-0000-000000000001"), tier="free")
    plus = user(UUID("00000000-0000-0000-0000-000000000002"), tier="plus")
    reader = FakeUsersReader(free, plus)

    compose = ScriptedCompose()
    everyone = RunWeeklyReviewsUseCase(
        users_reader=reader,
        compose=compose,  # type: ignore[arg-type]
        clock=FixedClock(),
        audience="all",
    )
    counts = await everyone.execute()
    assert counts == {"generated": 2, "skipped": 0, "failed": 0}
    assert reader.asked_tier == [None]

    compose_plus = ScriptedCompose()
    plus_only = RunWeeklyReviewsUseCase(
        users_reader=reader,
        compose=compose_plus,  # type: ignore[arg-type]
        clock=FixedClock(),
        audience="plus",
    )
    await plus_only.execute()
    assert compose_plus.seen == [plus.user_id]
