"""The agent's feed: what deserves your attention, computed the moment you ask.

Rule insights cost nothing and can never go stale because they are derived
on-read from the same snapshots the screens show — the only stored fact is the
user's "stop showing me this one" (a dismissal key). LLM outputs join the feed
in the proactive stage that follows.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Final
from uuid import UUID

from pydantic import BaseModel

from src.modules.assistant.application.dto.insights import (
    CapAlertInsight,
    InsightDTO,
    UncategorizedInsight,
    UpcomingChargeInsight,
)
from src.modules.assistant.application.dto.outputs import AgentOutputDTO
from src.modules.assistant.application.ports.agent_output_repository import (
    AgentOutputRepository,
)
from src.modules.assistant.application.ports.budgets_reader import BudgetsReader
from src.modules.assistant.application.ports.categories_reader import CategoriesReader
from src.modules.assistant.application.ports.insight_dismissals import InsightDismissals
from src.modules.assistant.application.ports.movements_reader import MovementsReader
from src.modules.assistant.application.ports.subscriptions_reader import SubscriptionsReader
from src.modules.assistant.domain.entities.agent_output import (
    MONTHLY_SUMMARY,
    WEEKLY_REVIEW,
    AgentOutput,
)
from src.shared.domain.period import MonthPeriod

CAP_ALERT_USED: Final[float] = 0.8
UPCOMING_DAYS: Final[int] = 2
UNCATEGORIZED_MIN: Final[int] = 3
UPCOMING_LIMIT: Final[int] = 10
WEEKLY_FEED_DAYS: Final[int] = 14


class FeedInputDTO(BaseModel):
    user_id: UUID
    currency: str
    today: str


class FeedDTO(BaseModel):
    insights: list[InsightDTO]
    outputs: list[AgentOutputDTO]
    unseen_count: int


@dataclass
class GetAssistantFeedUseCase:
    budgets_reader: BudgetsReader
    subscriptions_reader: SubscriptionsReader
    movements_reader: MovementsReader
    categories_reader: CategoriesReader
    dismissals: InsightDismissals
    outputs: AgentOutputRepository

    async def execute(self, input_dto: FeedInputDTO) -> FeedDTO:
        insights = [
            *await self._cap_alerts(input_dto),
            *await self._upcoming_charges(input_dto),
            *await self._uncategorized(input_dto),
        ]
        if insights:
            dismissed = await self.dismissals.dismissed_among(
                input_dto.user_id, [insight.key for insight in insights]
            )
            insights = [i for i in insights if i.key not in dismissed]
        outputs = await self._current_outputs(input_dto)
        return FeedDTO(
            insights=insights,
            outputs=[AgentOutputDTO.from_domain(o) for o in outputs],
            unseen_count=sum(1 for o in outputs if o.read_at is None),
        )

    async def _current_outputs(self, input_dto: FeedInputDTO) -> list[AgentOutput]:
        """The vigentes: the latest Corte (it reigns until the next one lands)
        and a weekly review while it is still this-week news. Dismissed ones
        leave the feed but never the shelf."""
        current: list[AgentOutput] = []
        monthly = await self.outputs.latest(input_dto.user_id, MONTHLY_SUMMARY, 1)
        if monthly and monthly[0].dismissed_at is None:
            current.append(monthly[0])
        weekly = await self.outputs.latest(input_dto.user_id, WEEKLY_REVIEW, 1)
        if weekly and weekly[0].dismissed_at is None:
            today = date.fromisoformat(input_dto.today)
            age = (today - weekly[0].created_at.date()).days
            if age <= WEEKLY_FEED_DAYS:
                current.append(weekly[0])
        return current

    async def _cap_alerts(self, input_dto: FeedInputDTO) -> list[InsightDTO]:
        snapshot = await self.budgets_reader.snapshot(
            input_dto.user_id, input_dto.currency, input_dto.today
        )
        names = {c.id: c.name for c in await self.categories_reader.all(input_dto.user_id)}
        alerts: list[InsightDTO] = []
        if snapshot.month is not None and snapshot.month.used >= CAP_ALERT_USED:
            alerts.append(
                CapAlertInsight(
                    kind="cap_alert",
                    key=f"cap:global:{snapshot.period}",
                    scope="global",
                    category_id=None,
                    category_name=None,
                    used=snapshot.month.used,
                    target=snapshot.month.target,
                    spent=snapshot.month.spent,
                    over=snapshot.month.over,
                )
            )
        for cap in snapshot.categories:
            if cap.used >= CAP_ALERT_USED:
                alerts.append(
                    CapAlertInsight(
                        kind="cap_alert",
                        key=f"cap:{cap.category_id}:{snapshot.period}",
                        scope="category",
                        category_id=cap.category_id,
                        category_name=names.get(cap.category_id, "?"),
                        used=cap.used,
                        target=cap.target,
                        spent=cap.spent,
                        over=cap.over,
                    )
                )
        return alerts

    async def _upcoming_charges(self, input_dto: FeedInputDTO) -> list[InsightDTO]:
        horizon = (date.fromisoformat(input_dto.today) + timedelta(days=UPCOMING_DAYS)).isoformat()
        charges = await self.subscriptions_reader.upcoming_charges(
            input_dto.user_id, input_dto.currency, input_dto.today, horizon, UPCOMING_LIMIT
        )
        return [
            UpcomingChargeInsight(
                kind="upcoming_charge",
                # Pending charges have their own id; scheduled ones key by what
                # they are (sub + date), so tomorrow's dismissal is tomorrow's.
                key=f"charge:{charge.charge_id or f'{charge.subscription_id}:{charge.due_on}'}",
                subscription_id=charge.subscription_id,
                name=charge.subscription_name,
                amount=charge.amount,
                due_on=charge.due_on,
                charge_id=charge.charge_id,
            )
            for charge in charges
        ]

    async def _uncategorized(self, input_dto: FeedInputDTO) -> list[InsightDTO]:
        period = MonthPeriod.containing(date.fromisoformat(input_dto.today))
        summary = await self.movements_reader.summary(
            input_dto.user_id, period.first_day, input_dto.today
        )
        bucket = next((c for c in summary.by_category if c.category_id is None), None)
        if bucket is None or bucket.count < UNCATEGORIZED_MIN:
            return []
        return [
            UncategorizedInsight(
                kind="uncategorized",
                key=f"uncat:{period.key}",
                count=bucket.count,
                spent=bucket.spent,
            )
        ]
