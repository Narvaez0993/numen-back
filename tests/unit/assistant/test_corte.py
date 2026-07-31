"""El Corte: adaptive playlist, deterministic play choice, narration that can
degrade but never block, and the cross-tenant sweep."""

from datetime import UTC, datetime
from uuid import UUID

from src.modules.assistant.application.ports.agent_model import ToolCall
from src.modules.assistant.application.ports.budgets_reader import (
    BudgetsView,
    CapView,
    CategoryCapView,
)
from src.modules.assistant.application.ports.goals_reader import GoalView
from src.modules.assistant.application.ports.movements_reader import (
    CategorySpendView,
    DaySpendView,
    PeriodSummaryView,
)
from src.modules.assistant.application.ports.users_reader import UserView
from src.modules.assistant.application.services.corte_composer import (
    CorteFacts,
    PlayDraft,
    compose_slides,
    pick_monthly_play,
)
from src.modules.assistant.application.services.narration import (
    NarrationItem,
    apply_narration,
)
from src.modules.assistant.application.use_cases.compose_monthly_summary import (
    ComposeMonthlySummaryUseCase,
)
from src.modules.assistant.application.use_cases.run_monthly_summaries import (
    RunMonthlySummariesUseCase,
)
from src.modules.assistant.domain.entities.agent_output import MONTHLY_SUMMARY
from src.modules.assistant.domain.errors import AgentUnavailableError
from tests.unit.assistant.fakes import (
    PRICING,
    USER_ID,
    FailingAgentModel,
    FakeActionLog,
    FakeAgentModel,
    FakeAgentOutputRepository,
    FakeCategoriesReader,
    turn,
)

PERIOD = "2026-07"
NOW = datetime(2026, 8, 1, 6, 0, 0, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


def summary(
    *,
    expense: int = 1_250_000,
    income: int = 0,
    count: int = 12,
    by_category: tuple[CategorySpendView, ...] = (),
) -> PeriodSummaryView:
    return PeriodSummaryView(
        date_from="2026-07-01",
        date_to="2026-07-31",
        expense_total=expense,
        income_total=income,
        count=count,
        by_category=by_category,
    )


def category(cid: str | None, spent: int, count: int = 3) -> CategorySpendView:
    return CategorySpendView(category_id=cid, spent=spent, count=count)


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


def budgets(
    *, month: CapView | None = None, categories: tuple[CategoryCapView, ...] = ()
) -> BudgetsView:
    return BudgetsView(period=PERIOD, days_left=0, month=month, categories=categories)


def goal(*, pct: float = 0.64, archived: bool = False) -> GoalView:
    return GoalView(
        id="g-1",
        name="Viaje",
        target=5_000_000,
        saved=int(5_000_000 * pct),
        pct=pct,
        achieved=False,
        archived=archived,
        target_date="2026-12-31",
        projected_on=None,
        needed_per_month=400_000,
    )


def facts(**overrides: object) -> CorteFacts:
    base: dict[str, object] = {
        "period": PERIOD,
        "summary": summary(
            by_category=(category("comida", 500_000, 8), category("transporte", 200_000, 4))
        ),
        "previous": summary(expense=1_360_000, count=10),
        "days": (
            DaySpendView(day="2026-07-03", spent=80_000, count=2),
            DaySpendView(day="2026-07-18", spent=300_000, count=5),
        ),
        "category_names": {"comida": "Comida", "transporte": "Transporte"},
        "budgets": budgets(),
        "goals": (goal(),),
        "tier": "free",
        "category_caps_free_limit": 2,
    }
    base.update(overrides)
    return CorteFacts(**base)  # type: ignore[arg-type]


# --- the adaptive playlist ---


def test_full_playlist_in_narrative_order() -> None:
    slides = compose_slides(facts(), play_id="p-1")
    assert [s["type"] for s in slides] == [
        "cover",
        "big_number",
        "category_bars",
        "fun_fact",
        "pulse",
        "goal",
        "play",
    ]


def test_first_month_replaces_pulse() -> None:
    slides = compose_slides(facts(previous=summary(expense=0, count=0)), play_id=None)
    types = [s["type"] for s in slides]
    assert "first_month" in types
    assert "pulse" not in types


def test_thin_facts_shrink_the_playlist() -> None:
    thin = facts(
        summary=summary(by_category=()),
        days=(DaySpendView(day="2026-07-10", spent=50_000, count=1),),
        goals=(),
        previous=summary(expense=0, count=3),
    )
    slides = compose_slides(thin, play_id=None)
    assert [s["type"] for s in slides] == ["cover", "big_number"]


def test_bars_cap_at_three_and_carry_names() -> None:
    many = facts(
        summary=summary(
            by_category=(
                category("comida", 500_000),
                category("transporte", 200_000),
                category("ocio", 150_000),
                category("otros", 100_000),
                category(None, 90_000),
            )
        ),
        category_names={"comida": "Comida", "transporte": "Transporte", "ocio": "Ocio"},
    )
    bars = next(s for s in compose_slides(many, None) if s["type"] == "category_bars")["bars"]
    assert [b["name"] for b in bars] == ["Comida", "Transporte", "Ocio"]
    assert bars[0]["pct"] == 500_000 / 1_250_000


def test_fun_fact_needs_two_spending_days() -> None:
    one_day = facts(days=(DaySpendView(day="2026-07-10", spent=300_000, count=4),))
    assert all(s["type"] != "fun_fact" for s in compose_slides(one_day, None))

    heaviest = next(s for s in compose_slides(facts(), None) if s["type"] == "fun_fact")
    assert heaviest["day"] == "2026-07-18"


# --- the deterministic play ---


def test_broken_cap_wins_and_raises_to_a_nice_number() -> None:
    broken = facts(
        budgets=budgets(
            categories=(
                cap("comida", 300_000, 487_450, bid="b-comida"),
                cap("transporte", 200_000, 150_000, bid="b-transporte"),
            )
        )
    )
    draft = pick_monthly_play(broken)
    assert draft == PlayDraft(
        action="raise_category_cap",
        params={
            "budget_id": "b-comida",
            "category_id": "comida",
            "category_name": "Comida",
            "current_target": 300_000,
            "target": 490_000,
        },
    )


def test_biggest_uncapped_category_gets_a_cap_with_goal_link() -> None:
    draft = pick_monthly_play(facts())
    assert draft is not None
    assert draft.action == "set_category_cap"
    assert draft.params["category_id"] == "comida"
    assert draft.params["target"] == 450_000  # 0.9 · 500k, already nice
    assert draft.params["linked_goal_id"] == "g-1"


def test_free_tier_without_slots_falls_through_to_month_cap() -> None:
    full = facts(
        budgets=budgets(
            categories=(
                cap("arriendo", 900_000, 100_000, bid="b-a"),
                cap("mercado", 400_000, 100_000, bid="b-m"),
            )
        )
    )
    draft = pick_monthly_play(full)
    assert draft is not None
    assert draft.action == "set_month_cap"
    assert draft.params == {"target": 1_300_000}


def test_nothing_to_play_when_all_is_capped() -> None:
    month = CapView(
        id="b-g",
        target=2_000_000,
        spent=1_250_000,
        remaining=750_000,
        per_day=None,
        projected=None,
        over=None,
        used=0.625,
    )
    covered = facts(
        budgets=budgets(
            month=month,
            categories=(
                cap("comida", 600_000, 500_000, bid="b-c"),
                cap("transporte", 300_000, 200_000, bid="b-t"),
            ),
        )
    )
    assert pick_monthly_play(covered) is None


# --- narration: degrade, never block ---

ITEMS = [
    NarrationItem(item_id="cover", kind="cover", data={}),
    NarrationItem(item_id="big_number", kind="big_number", data={"amount": 1}),
]


def test_narration_applies_covered_items() -> None:
    texts = apply_narration(
        {
            "items": [
                {"item_id": "cover", "text": "Tu julio, contado."},
                {"item_id": "big_number", "text": "Se movió con ritmo."},
            ]
        },
        ITEMS,
        "es",
    )
    assert texts == {"cover": "Tu julio, contado.", "big_number": "Se movió con ritmo."}


def test_narration_falls_back_per_missing_or_invalid_item() -> None:
    texts = apply_narration(
        {
            "items": [
                {"item_id": "cover", "text": ""},
                {"item_id": "big_number", "text": "x" * 200},
            ]
        },
        ITEMS,
        "es",
    )
    assert texts["cover"] == "Tu mes, en corto."
    assert texts["big_number"] == "Así se movió tu plata este mes."


def test_narration_survives_no_arguments_at_all() -> None:
    texts = apply_narration(None, ITEMS, "en")
    assert texts["cover"] == "Your month, in short."


# --- the compose use case ---


def user(uid: UUID = USER_ID, language: str = "es") -> UserView:
    return UserView(user_id=uid, tier="free", language=language, currency="COP", objective=None)


class StubMovementsReader:
    def __init__(self, current: PeriodSummaryView, previous: PeriodSummaryView) -> None:
        self.by_span = {
            (current.date_from, current.date_to): current,
            (previous.date_from, previous.date_to): previous,
        }
        self.days: tuple[DaySpendView, ...] = (
            DaySpendView(day="2026-07-03", spent=80_000, count=2),
            DaySpendView(day="2026-07-18", spent=300_000, count=5),
        )

    async def summary(self, user_id: UUID, date_from: str, date_to: str) -> PeriodSummaryView:
        return self.by_span[(date_from, date_to)]

    async def spend_by_day(
        self, user_id: UUID, date_from: str, date_to: str
    ) -> tuple[DaySpendView, ...]:
        return self.days


class StubBudgetsReader:
    def __init__(self) -> None:
        self.asked_today: str | None = None

    async def snapshot(self, user_id: UUID, currency: str, today: str) -> BudgetsView:
        self.asked_today = today
        return budgets()


class StubGoalsReader:
    def __init__(self) -> None:
        self.asked_today: str | None = None

    async def snapshot(self, user_id: UUID, currency: str, today: str) -> tuple[GoalView, ...]:
        self.asked_today = today
        return (goal(),)


def june() -> PeriodSummaryView:
    return PeriodSummaryView(
        date_from="2026-06-01",
        date_to="2026-06-30",
        expense_total=1_360_000,
        income_total=0,
        count=9,
        by_category=(),
    )


def narrate_everything(call_args: dict) -> ToolCall:
    return ToolCall(id="c-1", name="narrate", arguments=call_args)


def build_compose(
    model: FakeAgentModel | FailingAgentModel,
    outputs: FakeAgentOutputRepository,
    log: FakeActionLog,
    movements: StubMovementsReader,
) -> tuple[ComposeMonthlySummaryUseCase, StubBudgetsReader, StubGoalsReader]:
    budgets_reader = StubBudgetsReader()
    goals_reader = StubGoalsReader()
    use_case = ComposeMonthlySummaryUseCase(
        outputs=outputs,
        movements_reader=movements,  # type: ignore[arg-type]
        budgets_reader=budgets_reader,
        goals_reader=goals_reader,
        categories_reader=FakeCategoriesReader(),
        agent_model=model,
        action_log=log,
        clock=FixedClock(),
        pricing=PRICING,
        model_name="claude-sonnet-5",
        category_caps_free_limit=2,
    )
    return use_case, budgets_reader, goals_reader


def rich_july() -> PeriodSummaryView:
    return summary(by_category=(category("comida", 500_000, 8), category("transporte", 200_000, 4)))


async def test_compose_creates_a_narrated_corte() -> None:
    outputs = FakeAgentOutputRepository()
    log = FakeActionLog()

    def scripted(messages):
        import json

        request = json.loads(messages[-1].text)
        return turn(
            tool_calls=(
                narrate_everything(
                    {
                        "items": [
                            {"item_id": i["item_id"], "text": f"Línea de {i['item_id']}."}
                            for i in request["items"]
                        ]
                    }
                ),
            )
        )

    model = FakeAgentModel([scripted])
    use_case, budgets_reader, goals_reader = build_compose(
        model, outputs, log, StubMovementsReader(rich_july(), june())
    )

    output_id = await use_case.execute(user(), PERIOD)

    assert output_id is not None
    stored = outputs.outputs[output_id]
    slide_types = [s["type"] for s in stored.payload["slides"]]
    assert slide_types[0] == "cover"
    assert "play" in slide_types
    assert stored.payload["slides"][0]["text"] == "Línea de cover."
    assert len(stored.plays) == 1
    assert stored.plays[0].action == "set_category_cap"
    assert stored.plays[0].text.startswith("Línea de play:")
    # Budgets answered about the month under review; goals about the real today.
    assert budgets_reader.asked_today == "2026-07-31"
    assert goals_reader.asked_today == "2026-08-01"
    assert model.requests[0]["force_tool"] == "narrate"
    assert log.entries[0].action == "monthly_summary"
    assert log.entries[0].failed is False


async def test_compose_skips_thin_months_without_calling_the_model() -> None:
    outputs = FakeAgentOutputRepository()
    model = FakeAgentModel([])
    use_case, _, _ = build_compose(
        model,
        outputs,
        FakeActionLog(),
        StubMovementsReader(summary(count=2, by_category=()), june()),
    )

    assert await use_case.execute(user(), PERIOD) is None
    assert outputs.outputs == {}
    assert model.requests == []


async def test_compose_skips_when_the_period_already_exists() -> None:
    outputs = FakeAgentOutputRepository()
    from tests.unit.assistant.fakes import agent_output

    await outputs.add(agent_output(kind=MONTHLY_SUMMARY, period=PERIOD))
    model = FakeAgentModel([])
    use_case, _, _ = build_compose(
        model, outputs, FakeActionLog(), StubMovementsReader(rich_july(), june())
    )

    assert await use_case.execute(user(), PERIOD) is None
    assert model.requests == []


async def test_model_down_ships_the_corte_with_fallbacks() -> None:
    outputs = FakeAgentOutputRepository()
    log = FakeActionLog()
    use_case, _, _ = build_compose(
        FailingAgentModel(AgentUnavailableError()),
        outputs,
        log,
        StubMovementsReader(rich_july(), june()),
    )

    output_id = await use_case.execute(user(), PERIOD)

    assert output_id is not None
    cover = outputs.outputs[output_id].payload["slides"][0]
    assert cover["text"] == "Tu mes, en corto."
    assert log.entries[0].failed is True
    assert log.entries[0].cost_usd == 0.0


# --- the sweep ---


class FakeUsersReader:
    def __init__(self, *users: UserView) -> None:
        self.users = users

    async def list_users(self, tier: str | None = None) -> tuple[UserView, ...]:
        return tuple(u for u in self.users if tier is None or u.tier == tier)


class ScriptedCompose:
    """Stands in for ComposeMonthlySummaryUseCase: user → id | None | raise."""

    def __init__(self, script: dict[UUID, str | None | Exception]) -> None:
        self.script = script
        self.periods: list[str] = []

    async def execute(self, user: UserView, period: str) -> str | None:
        self.periods.append(period)
        result = self.script[user.user_id]
        if isinstance(result, Exception):
            raise result
        return result


async def test_sweep_counts_and_survives_failures() -> None:
    ok = user(UUID("00000000-0000-0000-0000-000000000001"))
    thin = user(UUID("00000000-0000-0000-0000-000000000002"))
    broken = user(UUID("00000000-0000-0000-0000-000000000003"))
    compose = ScriptedCompose(
        {ok.user_id: "out-1", thin.user_id: None, broken.user_id: RuntimeError("boom")}
    )
    sweep = RunMonthlySummariesUseCase(
        users_reader=FakeUsersReader(ok, thin, broken),
        compose=compose,  # type: ignore[arg-type]
        clock=FixedClock(),
    )

    counts = await sweep.execute()

    assert counts == {"generated": 1, "skipped": 1, "failed": 1}
    assert compose.periods == [PERIOD, PERIOD, PERIOD]  # Aug 1 reviews July
