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
from src.modules.assistant.domain.entities.debt_draft import PAYMENT, DebtDraft
from src.modules.assistant.domain.entities.movement_draft import MovementDraft
from src.modules.assistant.domain.usage import registrations_available
from src.shared.domain.money import to_minor_units
from src.shared.domain.period import MonthPeriod

RESPOND_TOOL: Final[str] = "respond_with_blocks"
STAGE_TOOL: Final[str] = "stage_movement_draft"
STAGE_DEBT_TOOL: Final[str] = "stage_debt_draft"
STAGE_DEBT_PAYMENT_TOOL: Final[str] = "stage_debt_payment_draft"

STAGE_TOOLS: Final[frozenset[str]] = frozenset(
    {STAGE_TOOL, STAGE_DEBT_TOOL, STAGE_DEBT_PAYMENT_TOOL}
)
"""What a capture is allowed to produce. Both are registrations, both end in a
confirm card, and which one fits is the model's read of the sentence — "le presté
5.000 a Andrés" is not an expense, and forcing the movement tool would make it one."""

MOVEMENT_TYPES: Final[frozenset[str]] = frozenset({"expense", "income", "transfer"})
DEBT_DIRECTIONS: Final[frozenset[str]] = frozenset({"incoming", "outgoing"})
MAX_COUNTERPARTY_NAME = 60
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
    capture_source: str = "text"
    """Where the words came from (`text` | `voice`) — stamped onto the draft.
    Deliberately NOT a tool parameter: provenance is the caller's fact, and a
    schema change would shift the cached prompt prefix."""


@dataclass(frozen=True)
class ToolOutcome:
    content: str
    is_error: bool = False
    draft: MovementDraft | None = None
    debt_draft: DebtDraft | None = None
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
        if call.name == STAGE_DEBT_TOOL:
            return await self._stage_debt(args, ctx)
        if call.name == STAGE_DEBT_PAYMENT_TOOL:
            return await self._stage_debt_payment(args, ctx)
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
            charges = await self.subscriptions.upcoming_charges(
                ctx.user_id, ctx.currency, ctx.today, date_to
            )
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
        source_id: str | None = str(args.get("source_id") or "") or None
        source_type: str | None = None
        if source_id is None:
            # The capture never said where the money came from. Guessing reads as
            # the app deciding for you — the draft goes out without a source and
            # the confirm card asks. The exception is a user who owns exactly one
            # source: there is nothing to choose, so choosing is not a guess.
            source_id, source_type = _only_source(sources)
        else:
            source_type = _resolve_source_type(sources, source_id)
            if source_type is None:
                raise ValueError(
                    f"unknown source_id: {source_id!r} — use ids from the context catalog"
                )

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
            captured_via=ctx.capture_source,
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

    async def _stage_debt(self, args: dict[str, Any], ctx: ToolContext) -> ToolOutcome:
        """A debt the user mentioned in passing — "le presté 50 mil a Andrés".

        Deliberately close to `_stage`: same quota gate, same "never guess the
        account" rule, same draft-then-card shape. What it adds is the person, and
        the one place it IS allowed to decide for the user: a spoken name that
        already matches someone in their ledger resolves to that person, because
        creating a second "Andrés" would split their debts across both.
        """
        if not registrations_available(
            ctx.registrations_used + ctx.staged_count, ctx.registrations_limit
        ):
            return ToolOutcome(
                content=_dump(
                    {
                        "error": "registration_quota_exhausted",
                        "hint": (
                            "The monthly AI-capture quota ran out. Tell the user plainly and "
                            "offer the manual form (a navigate block to /deudas works)."
                        ),
                    }
                ),
                is_error=True,
            )

        direction = str(args.get("direction", ""))
        if direction not in DEBT_DIRECTIONS:
            raise ValueError(f"direction must be one of {sorted(DEBT_DIRECTIONS)}")

        amount = to_minor_units(str(args.get("amount", "")), ctx.currency)
        if amount <= 0:
            raise ValueError("amount must be positive")

        name = " ".join(str(args.get("counterparty_name", "")).split())
        if len(name) < 2:
            raise ValueError("counterparty_name must have at least 2 characters")
        if len(name) > MAX_COUNTERPARTY_NAME:
            raise ValueError(f"counterparty_name too long (max {MAX_COUNTERPARTY_NAME})")

        due_on = str(args.get("due_on") or "") or None
        if due_on is not None:
            date.fromisoformat(due_on)

        note = " ".join(str(args.get("note") or "").split()) or None
        if note is not None and len(note) > MAX_DRAFT_DESCRIPTION:
            raise ValueError(f"note too long (max {MAX_DRAFT_DESCRIPTION} characters)")

        account_id: str | None = str(args.get("account_id") or "") or None
        if account_id is not None:
            sources = await self.accounts.overview(ctx.user_id, ctx.currency)
            if not any(account.id == account_id for account in sources.accounts):
                # Cards are not offered: lending on one is a cash advance, a
                # different product, and the card would be a silent wrong answer.
                raise ValueError(
                    f"unknown account_id: {account_id!r} — use an account id from the catalog"
                )

        people = (await self.debts.snapshot(ctx.user_id, ctx.currency, ctx.today)).people
        counterparty_id = next(
            (person.id for person in people if person.name.casefold() == name.casefold()), None
        )

        draft = DebtDraft.stage(
            user_id=ctx.user_id,
            currency=ctx.currency,
            direction=direction,
            counterparty_id=counterparty_id,
            counterparty_name=name,
            amount=amount,
            account_id=account_id,
            due_on=due_on,
            note=note,
            created_at=datetime.now(UTC),
            captured_via=ctx.capture_source,
        )
        normalized = {
            "debt_draft_id": draft.id,
            "direction": draft.direction,
            "counterparty_name": draft.counterparty_name,
            "amount_minor_units": draft.amount,
            "known_person": counterparty_id is not None,
        }
        return ToolOutcome(content=_dump(normalized), debt_draft=draft)

    async def _stage_debt_payment(self, args: dict[str, Any], ctx: ToolContext) -> ToolOutcome:
        """An abono on a debt that already exists — "Santiago me pagó 2.000".

        The whole job is finding WHICH debt, and the name is optional on purpose:
        people say "me pagaron 2.000 de una deuda" and expect the app to know what
        it already knows. So the rule is the same one the source picker follows —
        resolve when there is nothing to choose, ask when there is:

        * a name that matches one open debt → resolved;
        * no name and exactly one open debt → resolved, because a list of one is
          not a choice;
        * anything else → staged WITHOUT a target, and the card shows the user
          their own open debts to pick from. That is a better question than the
          agent asking "¿quién te pagó?" in words: the app has the list, the user
          does not have to remember it.

        Unlike a loan, this never accepts "no money moved": a repayment IS the money
        changing hands.
        """
        if not registrations_available(
            ctx.registrations_used + ctx.staged_count, ctx.registrations_limit
        ):
            return ToolOutcome(
                content=_dump(
                    {
                        "error": "registration_quota_exhausted",
                        "hint": (
                            "The monthly AI-capture quota ran out. Tell the user plainly and "
                            "offer the manual form (a navigate block to /deudas works)."
                        ),
                    }
                ),
                is_error=True,
            )

        amount = to_minor_units(str(args.get("amount", "")), ctx.currency)
        if amount <= 0:
            raise ValueError("amount must be positive")

        name = " ".join(str(args.get("counterparty_name") or "").split())
        snapshot = await self.debts.snapshot(ctx.user_id, ctx.currency, ctx.today)
        live = [debt for debt in snapshot.debts if debt.remaining > 0]
        if not live:
            return ToolOutcome(
                content=_dump(
                    {
                        "error": "no_open_debt",
                        "hint": (
                            "There is no open debt to pay down. Do not open one to pay it "
                            "off — tell the user and ask what they meant."
                        ),
                    }
                ),
                is_error=True,
            )

        candidates = (
            [debt for debt in live if debt.counterparty.casefold() == name.casefold()]
            if name
            else live
        )
        if name and not candidates:
            return ToolOutcome(
                content=_dump(
                    {
                        "error": "no_open_debt",
                        "hint": (
                            f"{name} has no open debt. Do not open one to pay it off — "
                            "tell the user and ask what they meant."
                        ),
                    }
                ),
                is_error=True,
            )

        # One candidate is not a guess; several is a question the CARD asks, with the
        # user's own debts in front of them.
        target = candidates[0] if len(candidates) == 1 else None
        if target is not None and amount > target.remaining:
            return ToolOutcome(
                content=_dump(
                    {
                        "error": "more_than_owed",
                        "hint": (
                            "That is more than what is left on the debt "
                            f"({target.remaining} minor units). Ask instead of clamping."
                        ),
                    }
                ),
                is_error=True,
            )

        account_id: str | None = str(args.get("account_id") or "") or None
        if account_id is not None:
            sources = await self.accounts.overview(ctx.user_id, ctx.currency)
            if not any(account.id == account_id for account in sources.accounts):
                raise ValueError(
                    f"unknown account_id: {account_id!r} — use an account id from the catalog"
                )

        resolved_name = target.counterparty if target is not None else name
        person = next(
            (p for p in snapshot.people if p.name.casefold() == resolved_name.casefold()),
            None,
        )
        draft = DebtDraft.stage(
            user_id=ctx.user_id,
            currency=ctx.currency,
            kind=PAYMENT,
            target_debt_id=target.id if target is not None else None,
            # The debt's own direction: it decides which way the cash flows back, and
            # so which question the card asks. Unknown until a debt is picked, and
            # `incoming` is the honest default — "me pagaron" is what people say.
            direction=(
                _DEBT_DIRECTIONS.get(target.direction, target.direction)
                if target is not None
                else "incoming"
            ),
            counterparty_id=person.id if person else None,
            counterparty_name=resolved_name,
            amount=amount,
            account_id=account_id,
            due_on=None,
            note=None,
            created_at=datetime.now(UTC),
            captured_via=ctx.capture_source,
        )
        normalized = {
            "debt_draft_id": draft.id,
            "kind": PAYMENT,
            "amount_minor_units": draft.amount,
            "resolved": target is not None,
            "hint": (
                None
                if target is not None
                else "The card is showing the user their open debts to pick from — "
                "do NOT ask which one in words."
            ),
        }
        return ToolOutcome(content=_dump(normalized), debt_draft=draft)


#: `DebtsReader` speaks the reader's words; the draft speaks the debts module's.
_DEBT_DIRECTIONS: Final[dict[str, str]] = {
    "owed_to_me": "incoming",
    "i_owe": "outgoing",
}


def _resolve_source_type(view: AccountsView, source_id: str) -> str | None:
    """The model only names an id; whether it is an account or a card is ours to know."""
    if any(account.id == source_id for account in view.accounts):
        return "account"
    if any(card.id == source_id for card in view.credit_cards):
        return "credit_card"
    return None


def _only_source(view: AccountsView) -> tuple[str | None, str | None]:
    """The single source a user owns, when they own exactly one — accounts and
    cards counted together, because to the person spending they are one list.
    Two or more is a choice, and choices belong to the user, not to us."""
    if len(view.accounts) == 1 and not view.credit_cards:
        return view.accounts[0].id, "account"
    if len(view.credit_cards) == 1 and not view.accounts:
        return view.credit_cards[0].id, "credit_card"
    return None, None


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
                "description": (
                    "Major units, as the user speaks them. A magnitude word "
                    "MULTIPLIES what comes before it and is never concatenated: "
                    "'25 mil' is 25000, and '3 millones 800' / '3 millones "
                    "ochocientos' are both 3800000 — never 3800. Dictation often "
                    "digitizes half a phrase and leaves the magnitude as a word, "
                    "so read the words, not the digit string. A bare number "
                    "trailing a magnitude takes the next rank down: after "
                    "'millones', '800' means 800 thousand. A number inside a "
                    "product name ('play 5', 'iphone 15') is neither a quantity "
                    "nor a price — never multiply the amount by it."
                ),
            },
            "description": {"type": "string", "maxLength": MAX_DRAFT_DESCRIPTION},
            "source_id": {
                "type": "string",
                "description": (
                    "Account or card id the money moves from. OMIT it when the "
                    "user did not say where the money came from — never guess, "
                    "not even when one source seems likelier. The confirm card "
                    "asks for it, and a wrong guess is worse than a question."
                ),
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
        ["type", "amount", "description"],
    ),
    _spec(
        STAGE_DEBT_TOOL,
        "Stage a DEBT draft when the user mentions money lent or borrowed between "
        "them and a person — 'le presté 50 mil a Andrés', 'mi amigo me debe 5.000', "
        "'le quedé debiendo a mi mamá'. This is NOT an expense: lending turns cash "
        "into a claim and the user is no poorer for it. It is not saved either — "
        "the user sees a confirmation card. Reference the returned debt_draft_id in "
        "a debt_draft block of your final answer, otherwise the draft is dropped.",
        {
            "direction": {
                "type": "string",
                "enum": sorted(DEBT_DIRECTIONS),
                "description": (
                    "Read from the USER's side. 'incoming' = they owe the user "
                    "(the user lent, or paid for someone). 'outgoing' = the user "
                    "owes them (someone lent to the user, or covered them)."
                ),
            },
            "counterparty_name": {
                "type": "string",
                "maxLength": MAX_COUNTERPARTY_NAME,
                "description": (
                    "The person as the user named them ('Andrés', 'mi mamá'). A "
                    "name, never an id — matching it to someone they already owe "
                    "is done for you."
                ),
            },
            "amount": {
                "type": ["number", "string"],
                "description": (
                    "Major units, as the user speaks them. A magnitude word "
                    "MULTIPLIES what comes before it and is never concatenated: "
                    "'25 mil' is 25000 and '3 millones 800' is 3800000, never 3800."
                ),
            },
            "account_id": {
                "type": "string",
                "description": (
                    "Account id the cash moved on, ONLY if the user said so. Omit "
                    "it otherwise — never guess: the card asks, and it also offers "
                    "'no money moved', which is the truth for a split bill."
                ),
            },
            "due_on": {
                "type": "string",
                "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                "description": "YYYY-MM-DD, only if the user gave a deadline.",
            },
            "note": {"type": "string", "maxLength": MAX_DRAFT_DESCRIPTION},
        },
        ["direction", "counterparty_name", "amount"],
    ),
    _spec(
        STAGE_DEBT_PAYMENT_TOOL,
        "Stage an ABONO on a debt that ALREADY EXISTS — 'Santiago me pagó 2.000', "
        "'le aboné 20 mil a mi mamá', 'me devolvieron la mitad'. Use this, never "
        f"{STAGE_DEBT_TOOL}, when the money is paying an existing debt DOWN: opening "
        "a second debt for the same person is the one mistake that quietly doubles "
        "what they owe. Not saved — the user sees a confirmation card. Reference the "
        "returned debt_draft_id in a debt_draft block of your final answer.",
        {
            "counterparty_name": {
                "type": "string",
                "maxLength": MAX_COUNTERPARTY_NAME,
                "description": (
                    "The person, ONLY if the user named them. OMIT it otherwise — "
                    "'me pagaron 2.000 de una deuda' names nobody, and that is fine: "
                    "the card shows the user their open debts to pick from. Never "
                    "ask 'who paid you?' in words; the app already has the list."
                ),
            },
            "amount": {
                "type": ["number", "string"],
                "description": (
                    "Major units, as the user speaks them. A magnitude word "
                    "MULTIPLIES what comes before it: '25 mil' is 25000."
                ),
            },
            "account_id": {
                "type": "string",
                "description": (
                    "Account id the money moved on, ONLY if the user said so. Omit "
                    "it otherwise — never guess. A repayment always moves cash, so "
                    "the card asks; there is no 'no money moved' answer here."
                ),
            },
        },
        ["amount"],
    ),
    ToolSpec(
        name=RESPOND_TOOL,
        description=(
            "Your final answer, ALWAYS — a list of typed blocks. Rules: every number "
            "you show must come from a tool result; draft blocks only reference a "
            f"draft_id returned by {STAGE_TOOL}; debt_draft blocks only reference a "
            f"debt_draft_id returned by {STAGE_DEBT_TOOL}; navigate routes must be one of: "
            + ", ".join(NAVIGATE_ROUTES)
            + f". At most {MAX_BLOCKS_PER_MESSAGE} blocks."
        ),
        input_schema=RespondWithBlocksInput.model_json_schema(),
    ),
)
