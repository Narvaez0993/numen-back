"""The agent's hands: every tool it can call, and what calling them does.

The registry composes the module's fine-grained ports into a `name → executor`
table. The chat loop never knows data sources — it knows tools. Two tools are
special and the loop treats them so: `stage_movement_draft` accumulates a draft
(returned in the outcome, persisted only with the final message) and
`respond_with_blocks` is terminal (declared here, intercepted by the loop).

The toolset is deliberately **immutable with respect to quotas**: removing a
tool per-request would shift the cached prompt prefix. When the registration
quota is gone the stage executor answers with an error result that tells the
model to say so and offer the manual form.
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Final
from uuid import UUID

from src.modules.assistant.application.dto.blocks import (
    MAX_BLOCKS_PER_MESSAGE,
    NAVIGATE_ROUTES,
    RespondWithBlocksInput,
)
from src.modules.assistant.application.ports.accounts_reader import AccountsReader, AccountsView
from src.modules.assistant.application.ports.agent_model import ToolCall, ToolSpec
from src.modules.assistant.application.ports.budgets_reader import BudgetsReader
from src.modules.assistant.application.ports.categories_reader import CategoriesReader
from src.modules.assistant.application.ports.debts_reader import DebtsReader
from src.modules.assistant.application.ports.goals_reader import GoalsReader
from src.modules.assistant.application.ports.movements_reader import MovementsReader
from src.modules.assistant.application.ports.subscriptions_reader import SubscriptionsReader
from src.modules.assistant.domain.entities.movement_draft import MovementDraft
from src.modules.assistant.domain.usage import registrations_available
from src.shared.domain.money import to_minor_units
from src.shared.domain.period import MonthPeriod

RESPOND_TOOL: Final[str] = "respond_with_blocks"
STAGE_TOOL: Final[str] = "stage_movement_draft"

MOVEMENT_TYPES: Final[frozenset[str]] = frozenset({"expense", "income", "transfer"})
MAX_DRAFT_DESCRIPTION = 80
_MONTH_SCHEMA: Final[dict[str, Any]] = {
    "type": "string",
    "pattern": "^\\d{4}-\\d{2}$",
    "description": "Month as YYYY-MM; omit for the current month.",
}


@dataclass(frozen=True)
class ToolContext:
    """Per-turn facts the executors need; rebuilt on every dispatch because
    `staged_count` moves as the model stages drafts within one turn."""

    user_id: UUID
    currency: str
    today: str
    registrations_used: int
    registrations_limit: int
    staged_count: int


@dataclass(frozen=True)
class ToolOutcome:
    content: str
    is_error: bool = False
    draft: MovementDraft | None = None
    is_read: bool = False


def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _month_range(month: str | None, today: str) -> tuple[str, str]:
    """`YYYY-MM` (or the month of `today`) → its first and last day."""
    if month is None:
        period = MonthPeriod.containing(date.fromisoformat(today))
    else:
        period = MonthPeriod.containing(date.fromisoformat(f"{month}-01"))
    return period.first_day, period.last_day


@dataclass
class ToolRegistry:
    accounts: AccountsReader
    movements: MovementsReader
    budgets: BudgetsReader
    goals: GoalsReader
    debts: DebtsReader
    subscriptions: SubscriptionsReader
    categories: CategoriesReader

    def specs(self) -> tuple[ToolSpec, ...]:
        return _SPECS

    async def execute(self, call: ToolCall, ctx: ToolContext) -> ToolOutcome:
        try:
            return await self._dispatch(call, ctx)
        except (ValueError, KeyError, TypeError) as exc:
            return ToolOutcome(content=_dump({"error": str(exc)}), is_error=True)

    async def _dispatch(self, call: ToolCall, ctx: ToolContext) -> ToolOutcome:
        args = call.arguments
        if call.name == STAGE_TOOL:
            return await self._stage(args, ctx)
        if call.name == "get_accounts_overview":
            view = await self.accounts.overview(ctx.user_id, ctx.currency)
            return ToolOutcome(content=_dump(asdict(view)), is_read=True)
        if call.name == "get_month_summary":
            date_from, date_to = _month_range(args.get("month"), ctx.today)
            summary = await self.movements.summary(ctx.user_id, date_from, date_to)
            return ToolOutcome(content=_dump(asdict(summary)), is_read=True)
        if call.name == "list_recent_movements":
            limit = min(int(args.get("limit", 10)), 30)
            recent = await self.movements.recent(ctx.user_id, limit)
            return ToolOutcome(content=_dump([asdict(m) for m in recent]), is_read=True)
        if call.name == "get_top_merchants":
            date_from, date_to = _month_range(args.get("month"), ctx.today)
            limit = min(int(args.get("limit", 5)), 10)
            merchants = await self.movements.top_merchants(ctx.user_id, date_from, date_to, limit)
            return ToolOutcome(content=_dump([asdict(m) for m in merchants]), is_read=True)
        if call.name == "get_budgets_snapshot":
            budgets = await self.budgets.snapshot(ctx.user_id, ctx.currency, ctx.today)
            return ToolOutcome(content=_dump(asdict(budgets)), is_read=True)
        if call.name == "get_goals_snapshot":
            goals = await self.goals.snapshot(ctx.user_id, ctx.currency, ctx.today)
            return ToolOutcome(content=_dump([asdict(g) for g in goals]), is_read=True)
        if call.name == "get_debts_snapshot":
            debts = await self.debts.snapshot(ctx.user_id, ctx.currency, ctx.today)
            return ToolOutcome(content=_dump(asdict(debts)), is_read=True)
        if call.name == "list_subscriptions":
            subs = await self.subscriptions.subscriptions(ctx.user_id, ctx.currency, ctx.today)
            return ToolOutcome(content=_dump(asdict(subs)), is_read=True)
        if call.name == "list_upcoming_charges":
            days = min(int(args.get("days_ahead", 14)), 60)
            date_to = (date.fromisoformat(ctx.today) + timedelta(days=days)).isoformat()
            charges = await self.subscriptions.upcoming_charges(ctx.user_id, ctx.today, date_to)
            return ToolOutcome(content=_dump([asdict(c) for c in charges]), is_read=True)
        if call.name == "list_categories":
            cats = await self.categories.all(ctx.user_id)
            return ToolOutcome(content=_dump([asdict(c) for c in cats]), is_read=True)
        return ToolOutcome(content=_dump({"error": f"Unknown tool: {call.name}"}), is_error=True)

    async def _stage(self, args: dict[str, Any], ctx: ToolContext) -> ToolOutcome:
        if not registrations_available(
            ctx.registrations_used + ctx.staged_count, ctx.registrations_limit
        ):
            return ToolOutcome(
                content=_dump(
                    {
                        "error": "registration_quota_exhausted",
                        "hint": (
                            "The monthly AI-capture quota ran out. Tell the user plainly and "
                            "offer the manual form (a navigate block to /movements works)."
                        ),
                    }
                ),
                is_error=True,
            )

        type_ = str(args.get("type", ""))
        if type_ not in MOVEMENT_TYPES:
            raise ValueError(f"type must be one of {sorted(MOVEMENT_TYPES)}")

        amount = to_minor_units(str(args.get("amount", "")), ctx.currency)
        if amount <= 0:
            raise ValueError("amount must be positive")

        description = " ".join(str(args.get("description", "")).split())
        if type_ != "transfer" and len(description) < 2:
            raise ValueError("description must have at least 2 characters")
        if len(description) > MAX_DRAFT_DESCRIPTION:
            raise ValueError(f"description too long (max {MAX_DRAFT_DESCRIPTION} characters)")

        occurred_on = str(args.get("occurred_on") or ctx.today)
        date.fromisoformat(occurred_on)
        if occurred_on > ctx.today:
            raise ValueError("occurred_on cannot be in the future")

        sources = await self.accounts.overview(ctx.user_id, ctx.currency)
        source_id = str(args.get("source_id", ""))
        source_type = _resolve_source_type(sources, source_id)
        if source_type is None:
            raise ValueError(f"unknown source_id: {source_id!r} — use ids from the context catalog")

        destination_id: str | None = None
        destination_type: str | None = None
        category_id = args.get("category_id")
        if type_ == "transfer":
            destination_id = str(args.get("destination_id", ""))
            destination_type = _resolve_source_type(sources, destination_id)
            if destination_type is None:
                raise ValueError(f"unknown destination_id: {destination_id!r}")
            if destination_id == source_id:
                raise ValueError("source and destination must differ")
            category_id = None
        elif category_id is not None:
            category_id = str(category_id)
            flows = {c.id: c.flow for c in await self.categories.all(ctx.user_id)}
            if category_id not in flows:
                raise ValueError(f"unknown category_id: {category_id!r}")
            expected_flow = "income" if type_ == "income" else "expense"
            if flows[category_id] != expected_flow:
                raise ValueError(f"category {category_id!r} is not a {expected_flow} category")

        draft = MovementDraft.stage(
            user_id=ctx.user_id,
            currency=ctx.currency,
            type=type_,
            description=description,
            amount=amount,
            source_type=source_type,
            source_id=source_id,
            destination_type=destination_type,
            destination_id=destination_id,
            category_id=category_id,
            occurred_on=occurred_on,
            created_at=datetime.now(UTC),
        )
        normalized = {
            "draft_id": draft.id,
            "type": draft.type,
            "amount_minor_units": draft.amount,
            "description": draft.description,
            "source_type": draft.source_type,
            "occurred_on": draft.occurred_on,
        }
        return ToolOutcome(content=_dump(normalized), draft=draft)


def _resolve_source_type(view: AccountsView, source_id: str) -> str | None:
    """The model only names an id; whether it is an account or a card is ours to know."""
    if any(account.id == source_id for account in view.accounts):
        return "account"
    if any(card.id == source_id for card in view.credit_cards):
        return "credit_card"
    return None


def _spec(name: str, description: str, properties: dict[str, Any], required: list[str]) -> ToolSpec:
    return ToolSpec(
        name=name,
        description=description,
        input_schema={
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    )


_SPECS: Final[tuple[ToolSpec, ...]] = (
    _spec(
        "get_accounts_overview",
        "The user's accounts and credit cards with current balances, plus totals "
        "(net balance, cash, card debt). Amounts in minor units.",
        {},
        [],
    ),
    _spec(
        "get_month_summary",
        "Expenses and income for a month: totals, movement count and spend per "
        "category_id. The ground truth for 'how am I doing this month'.",
        {"month": _MONTH_SCHEMA},
        [],
    ),
    _spec(
        "list_recent_movements",
        "The latest movements (newest first): type, description, amount, date, category.",
        {"limit": {"type": "integer", "minimum": 1, "maximum": 30, "default": 10}},
        [],
    ),
    _spec(
        "get_top_merchants",
        "Where the money went in a month, grouped by what the user wrote (merchant "
        "labels), largest first.",
        {
            "month": _MONTH_SCHEMA,
            "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
        },
        [],
    ),
    _spec(
        "get_budgets_snapshot",
        "The month cap and per-category caps: target, spent, remaining, per-day "
        "ceiling and whether the user is over.",
        {},
        [],
    ),
    _spec(
        "get_goals_snapshot",
        "Savings pockets: target, saved so far, progress, projection at the current "
        "pace and the monthly amount needed for a dated goal.",
        {},
        [],
    ),
    _spec(
        "get_debts_snapshot",
        "Open debts by counterparty in both directions (they owe / the user owes), "
        "with paid and remaining amounts.",
        {},
        [],
    ),
    _spec(
        "list_subscriptions",
        "Recurring charges the user registered: amount, frequency, next charge date, "
        "and monthly/yearly totals.",
        {},
        [],
    ),
    _spec(
        "list_upcoming_charges",
        "Subscription charges due in the next days.",
        {"days_ahead": {"type": "integer", "minimum": 1, "maximum": 60, "default": 14}},
        [],
    ),
    _spec(
        "list_categories",
        "Every category the user can classify a movement into, with its flow (expense or income).",
        {},
        [],
    ),
    _spec(
        STAGE_TOOL,
        "Stage a movement DRAFT from what the user said. It is NOT saved: the user "
        "sees a confirmation card. Amount goes in MAJOR units exactly as spoken "
        "('25 mil' pesos → 25000). Use ids from the context catalog. Reference the "
        "returned draft_id in a draft block of your final answer — otherwise the "
        "draft is dropped.",
        {
            "type": {"type": "string", "enum": sorted(MOVEMENT_TYPES)},
            "amount": {
                "type": ["number", "string"],
                "description": "Major units, as the user speaks them.",
            },
            "description": {"type": "string", "maxLength": MAX_DRAFT_DESCRIPTION},
            "source_id": {
                "type": "string",
                "description": "Account or card id the money moves from.",
            },
            "destination_id": {
                "type": "string",
                "description": "Transfers only: account or card id the money moves to.",
            },
            "category_id": {"type": "string"},
            "occurred_on": {
                "type": "string",
                "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                "description": "YYYY-MM-DD; omit for today. Never in the future.",
            },
        },
        ["type", "amount", "description", "source_id"],
    ),
    ToolSpec(
        name=RESPOND_TOOL,
        description=(
            "Your final answer, ALWAYS — a list of typed blocks. Rules: every number "
            "you show must come from a tool result; draft blocks only reference a "
            f"draft_id returned by {STAGE_TOOL}; navigate routes must be one of: "
            + ", ".join(NAVIGATE_ROUTES)
            + f". At most {MAX_BLOCKS_PER_MESSAGE} blocks."
        ),
        input_schema=RespondWithBlocksInput.model_json_schema(),
    ),
)
