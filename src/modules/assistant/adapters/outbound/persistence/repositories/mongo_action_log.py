import logging

from src.modules.assistant.adapters.outbound.persistence.documents.action_log_document import (
    AIActionLogDocument,
)
from src.modules.assistant.application.ports.action_log import ActionLogEntry

logger = logging.getLogger(__name__)


class MongoAIActionLog:
    """Beanie/Mongo implementation of `ActionLog`.

    Never raises, by port contract: this runs after the turn committed, and an
    analytics hiccup must not turn a served answer into a 500. No session on
    purpose — a failed turn still logs its cost.
    """

    async def record(self, entry: ActionLogEntry) -> None:
        try:
            await AIActionLogDocument(
                user_id=str(entry.user_id),
                action=entry.action,
                model=entry.model,
                calls=entry.calls,
                input_tokens=entry.input_tokens,
                output_tokens=entry.output_tokens,
                cache_read_tokens=entry.cache_read_tokens,
                cache_write_tokens=entry.cache_write_tokens,
                cost_usd=entry.cost_usd,
                period=entry.period,
                failed=entry.failed,
            ).insert()
        except Exception:
            logger.exception("ai_action_log_write_failed")
