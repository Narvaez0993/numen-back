"""One user's weekly review: read the finished ISO week, coach, persist.

Same machinery as the Corte (narrate-or-fallback, idempotent add, cost row),
different shape: a diagnosis instead of slides, up to three plays, and last
week's proposals echoed back with their CURRENT states — the accountability.
"""

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from src.modules.assistant.application.dto.plays import play_dto_from_domain
from src.modules.assistant.application.ports.action_log import ActionLog, ActionLogEntry
from src.modules.assistant.application.ports.agent_model import (
    ZERO_USAGE,
    AgentModel,
    ModelMessage,
    TokenUsage,
)
from src.modules.assistant.application.ports.agent_output_repository import (
    AgentOutputAlreadyExistsError,
    AgentOutputRepository,
)
from src.modules.assistant.application.ports.budgets_reader import BudgetsReader
from src.modules.assistant.application.ports.categories_reader import CategoriesReader
from src.modules.assistant.application.ports.goals_reader import GoalsReader
from src.modules.assistant.application.ports.movements_reader import MovementsReader
from src.modules.assistant.application.ports.subscriptions_reader import SubscriptionsReader
from src.modules.assistant.application.ports.users_reader import UserView
from src.modules.assistant.application.pricing import ModelPricing
from src.modules.assistant.application.services.corte_composer import PlayDraft
from src.modules.assistant.application.services.narration import (
    WEEKLY,
    NarrationItem,
    apply_narration,
    narration_request,
    narration_system_for,
)
from src.modules.assistant.application.services.narration_tools import (
    NARRATE_SPECS,
    NARRATE_TOOL,
)
from src.modules.assistant.application.services.weekly_composer import (
    WEEKLY_MIN_MOVEMENTS,
    WeeklyFacts,
    compose_weekly,
)
from src.modules.assistant.domain.entities.agent_output import (
    PLAY_PROPOSED,
    WEEKLY_REVIEW,
    AgentOutput,
    Play,
)
from src.modules.assistant.domain.errors import AgentUnavailableError
from src.modules.assistant.domain.periods import (
    iso_week_bounds,
    month_bounds,
    previous_iso_week_label,
)
from src.shared.application.ports.clock import Clock

PENDING_CHARGES_LIMIT = 50


@dataclass
class ComposeWeeklyReviewUseCase:
    outputs: AgentOutputRepository
    movements_reader: MovementsReader
    budgets_reader: BudgetsReader
    goals_reader: GoalsReader
    categories_reader: CategoriesReader
    subscriptions_reader: SubscriptionsReader
    agent_model: AgentModel
    action_log: ActionLog
    clock: Clock
    pricing: ModelPricing
    model_name: str
    treat_slack_fraction: float

    async def execute(self, user: UserView, period: str) -> str | None:
        if await self.outputs.find_by_period(user.user_id, WEEKLY_REVIEW, period):
            return None

        first, last = iso_week_bounds(period)
        week = await self.movements_reader.summary(user.user_id, first, last)
        if week.count < WEEKLY_MIN_MOVEMENTS:
            return None

        prev_first, prev_last = iso_week_bounds(previous_iso_week_label(period))
        previous_week = await self.movements_reader.summary(user.user_id, prev_first, prev_last)

        today = self.clock.now().date().isoformat()
        month_first, month_last = month_bounds(today[:7])
        month_to_date = await self.movements_reader.summary(user.user_id, month_first, today)
        charges = await self.subscriptions_reader.upcoming_charges(
            user.user_id, user.currency, today, month_last, PENDING_CHARGES_LIMIT
        )
        names = {c.id: c.name for c in await self.categories_reader.all(user.user_id)}
        budgets = await self.budgets_reader.snapshot(user.user_id, user.currency, today)
        goals = await self.goals_reader.snapshot(user.user_id, user.currency, today)

        previous_review = await self.outputs.find_by_period(
            user.user_id, WEEKLY_REVIEW, previous_iso_week_label(period)
        )

        facts = WeeklyFacts(
            period=period,
            week=week,
            previous_week=previous_week,
            month_to_date=month_to_date,
            pending_charges=sum(charge.amount for charge in charges),
            category_names=names,
            budgets=budgets,
            goals=goals,
            treat_slack_fraction=self.treat_slack_fraction,
            previous_plays=previous_review.plays if previous_review else (),
        )
        composition = compose_weekly(facts)

        drafts = [(str(uuid4()), draft) for draft in composition.plays]
        items = [
            NarrationItem(
                item_id="diagnosis",
                kind="weekly_diagnosis",
                data={
                    "week_total": composition.week_total,
                    "prev_week_total": composition.prev_week_total,
                    "delta_pct": composition.delta_pct,
                    "top_category_name": composition.top_category_name,
                    "plays": [draft.action for _, draft in drafts],
                    "accountability": list(composition.accountability),
                },
            )
        ]
        items.extend(
            NarrationItem(
                item_id=f"play:{play_id}",
                kind=draft.action,
                data={"action": draft.action, **dict(draft.params)},
            )
            for play_id, draft in drafts
        )
        texts, usage, failed, model = await self._narrate(items, user.language)

        plays = tuple(
            self._play(play_id, draft, texts[f"play:{play_id}"]) for play_id, draft in drafts
        )
        payload: dict[str, Any] = {
            "diagnosis_text": texts["diagnosis"],
            "week_total": composition.week_total,
            "prev_week_total": composition.prev_week_total,
            "delta_pct": composition.delta_pct,
            "top_category_id": composition.top_category_id,
            "top_category_name": composition.top_category_name,
            "accountability": list(composition.accountability),
        }

        output = AgentOutput(
            id=str(uuid4()),
            user_id=user.user_id,
            kind=WEEKLY_REVIEW,
            period=period,
            payload=payload,
            plays=plays,
            created_at=self.clock.now(),
            read_at=None,
            dismissed_at=None,
        )
        try:
            await self.outputs.add(output)
        except AgentOutputAlreadyExistsError:
            return None

        await self.action_log.record(
            ActionLogEntry(
                user_id=user.user_id,
                action="weekly_review",
                model=model,
                calls=1,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read_tokens=usage.cache_read_tokens,
                cache_write_tokens=usage.cache_write_tokens,
                cost_usd=self.pricing.cost_usd(usage),
                period=today[:7],
                failed=failed,
            )
        )
        return output.id

    @staticmethod
    def _play(play_id: str, draft: PlayDraft, text: str) -> Play:
        play = Play(
            id=play_id,
            action=draft.action,
            params=draft.params,
            text=text,
            status=PLAY_PROPOSED,
            result_id=None,
            failure_code=None,
            applied_at=None,
        )
        play_dto_from_domain(play)  # composition-time guard: params match the action
        return play

    async def _narrate(
        self, items: list[NarrationItem], language: str
    ) -> tuple[dict[str, str], TokenUsage, bool, str]:
        try:
            turn = await self.agent_model.respond(
                system=narration_system_for(language, WEEKLY),
                messages=(ModelMessage(role="user", text=narration_request(items)),),
                tools=NARRATE_SPECS,
                force_tool=NARRATE_TOOL,
            )
        except AgentUnavailableError:
            return apply_narration(None, items, language), ZERO_USAGE, True, self.model_name
        call = next((c for c in turn.tool_calls if c.name == NARRATE_TOOL), None)
        return (
            apply_narration(call.arguments if call else None, items, language),
            turn.usage,
            False,
            turn.model,
        )
