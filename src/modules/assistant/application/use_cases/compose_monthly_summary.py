"""One user's Corte: read the closed month, compose, narrate, persist.

The LLM's only job here is prose — one structured call, forced onto the
`narrate` tool. If the model is down the templates speak instead: a Corte is
never blocked by a provider, and its cost lands in the action log either way.
"""

from dataclasses import dataclass
from uuid import uuid4

from src.modules.assistant.application.dto.plays import play_dto_from_domain
from src.modules.assistant.application.dto.slides import SLIDES_ADAPTER
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
from src.modules.assistant.application.ports.users_reader import UserView
from src.modules.assistant.application.pricing import ModelPricing
from src.modules.assistant.application.services.corte_composer import (
    CORTE_MIN_MOVEMENTS,
    CorteFacts,
    compose_slides,
    pick_monthly_play,
)
from src.modules.assistant.application.services.narration import (
    NarrationItem,
    apply_narration,
    narration_request,
    narration_system_for,
)
from src.modules.assistant.application.services.narration_tools import (
    NARRATE_SPECS,
    NARRATE_TOOL,
)
from src.modules.assistant.domain.entities.agent_output import (
    MONTHLY_SUMMARY,
    PLAY_PROPOSED,
    AgentOutput,
    Play,
)
from src.modules.assistant.domain.errors import AgentUnavailableError
from src.modules.assistant.domain.periods import month_bounds, previous_month
from src.shared.application.ports.clock import Clock


@dataclass
class ComposeMonthlySummaryUseCase:
    outputs: AgentOutputRepository
    movements_reader: MovementsReader
    budgets_reader: BudgetsReader
    goals_reader: GoalsReader
    categories_reader: CategoriesReader
    agent_model: AgentModel
    action_log: ActionLog
    clock: Clock
    pricing: ModelPricing
    model_name: str
    category_caps_free_limit: int

    async def execute(self, user: UserView, period: str) -> str | None:
        """Returns the new output's id, or None when this user skips (already
        generated, or a month too thin to tell)."""
        if await self.outputs.find_by_period(user.user_id, MONTHLY_SUMMARY, period):
            return None

        first, last = month_bounds(period)
        summary = await self.movements_reader.summary(user.user_id, first, last)
        if summary.count < CORTE_MIN_MOVEMENTS:
            return None

        days = await self.movements_reader.spend_by_day(user.user_id, first, last)
        prev_first, prev_last = month_bounds(previous_month(first))
        previous = await self.movements_reader.summary(user.user_id, prev_first, prev_last)
        names = {c.id: c.name for c in await self.categories_reader.all(user.user_id)}
        # The month under review closed on `last` — snapshot budgets AS OF that
        # day, not the job's date, or we'd read the wrong month's caps.
        budgets = await self.budgets_reader.snapshot(user.user_id, user.currency, last)
        today = self.clock.now().date().isoformat()
        goals = await self.goals_reader.snapshot(user.user_id, user.currency, today)

        facts = CorteFacts(
            period=period,
            summary=summary,
            previous=previous,
            days=days,
            category_names=names,
            budgets=budgets,
            goals=goals,
            tier=user.tier,
            category_caps_free_limit=self.category_caps_free_limit,
        )
        draft = pick_monthly_play(facts)
        play_id = str(uuid4()) if draft else None
        slides_raw = compose_slides(facts, play_id)

        items = [
            NarrationItem(item_id=str(s["id"]), kind=str(s["type"]), data=s) for s in slides_raw
        ]
        if draft and play_id:
            items.append(
                NarrationItem(
                    item_id=f"play:{play_id}",
                    kind=draft.action,
                    data={"action": draft.action, **dict(draft.params)},
                )
            )
        texts, usage, failed, model = await self._narrate(items, user.language)

        slides = [{**raw, "text": texts[str(raw["id"])]} for raw in slides_raw]
        validated = SLIDES_ADAPTER.validate_python(slides)
        payload = {"slides": [s.model_dump() for s in validated]}

        plays: tuple[Play, ...] = ()
        if draft and play_id:
            play = Play(
                id=play_id,
                action=draft.action,
                params=draft.params,
                text=texts[f"play:{play_id}"],
                status=PLAY_PROPOSED,
                result_id=None,
                failure_code=None,
                applied_at=None,
            )
            play_dto_from_domain(play)  # composition-time guard: params match the action
            plays = (play,)

        output = AgentOutput(
            id=str(uuid4()),
            user_id=user.user_id,
            kind=MONTHLY_SUMMARY,
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
            # Two workers raced the same user — the other one's Corte counts.
            return None

        await self.action_log.record(
            ActionLogEntry(
                user_id=user.user_id,
                action="monthly_summary",
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

    async def _narrate(
        self, items: list[NarrationItem], language: str
    ) -> tuple[dict[str, str], TokenUsage, bool, str]:
        """(texts, usage, failed, model) — degraded prose is a warning, never an error."""
        try:
            turn = await self.agent_model.respond(
                system=narration_system_for(language),
                messages=(ModelMessage(role="user", text=narration_request(items)),),
                tools=NARRATE_SPECS,
                force_tool=NARRATE_TOOL,
            )
        except AgentUnavailableError:
            return (
                apply_narration(None, items, language),
                ZERO_USAGE,
                True,
                self.model_name,
            )
        call = next((c for c in turn.tool_calls if c.name == NARRATE_TOOL), None)
        texts = apply_narration(call.arguments if call else None, items, language)
        return texts, turn.usage, False, turn.model
