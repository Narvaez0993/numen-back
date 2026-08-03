"""The monthly sweep: every user gets last month's Corte, one at a time.

Users arrive ordered by language (the reader's contract), so the narrator's
static system prompt stays a cache hit across the whole sweep instead of
re-writing per user. One user failing never stops the rest.
"""

import logging
from dataclasses import dataclass

from src.modules.assistant.application.ports.users_reader import UsersReader
from src.modules.assistant.application.use_cases.compose_monthly_summary import (
    ComposeMonthlySummaryUseCase,
)
from src.modules.assistant.domain.periods import previous_month
from src.shared.application.ports.clock import Clock

logger = logging.getLogger(__name__)


@dataclass
class RunMonthlySummariesUseCase:
    users_reader: UsersReader
    compose: ComposeMonthlySummaryUseCase
    clock: Clock

    async def execute(self) -> dict[str, int]:
        period = previous_month(self.clock.now().date().isoformat())
        generated = skipped = failed = 0
        for user in await self.users_reader.list_users():
            try:
                output_id = await self.compose.execute(user, period)
            except Exception:
                failed += 1
                logger.exception(
                    "monthly_summary_failed",
                    extra={"user_id": str(user.user_id), "period": period},
                )
                continue
            if output_id is None:
                skipped += 1
            else:
                generated += 1
        return {"generated": generated, "skipped": skipped, "failed": failed}
