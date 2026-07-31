"""The Monday sweep: everyone in the audience gets last week's review.

`audience` is a Setting ("all" while the agent earns its keep, "plus" when
Fase 5 turns the paywall on) — the reader filters by tier, so the flip is
config, not code.
"""

import logging
from dataclasses import dataclass

from src.modules.assistant.application.ports.users_reader import UsersReader
from src.modules.assistant.application.use_cases.compose_weekly_review import (
    ComposeWeeklyReviewUseCase,
)
from src.modules.assistant.domain.periods import previous_iso_week
from src.shared.application.ports.clock import Clock

logger = logging.getLogger(__name__)


@dataclass
class RunWeeklyReviewsUseCase:
    users_reader: UsersReader
    compose: ComposeWeeklyReviewUseCase
    clock: Clock
    audience: str

    async def execute(self) -> dict[str, int]:
        period = previous_iso_week(self.clock.now().date().isoformat())
        tier = None if self.audience == "all" else self.audience
        generated = skipped = failed = 0
        for user in await self.users_reader.list_users(tier):
            try:
                output_id = await self.compose.execute(user, period)
            except Exception:
                failed += 1
                logger.exception(
                    "weekly_review_failed",
                    extra={"user_id": str(user.user_id), "period": period},
                )
                continue
            if output_id is None:
                skipped += 1
            else:
                generated += 1
        return {"generated": generated, "skipped": skipped, "failed": failed}
