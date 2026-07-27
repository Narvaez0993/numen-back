from typing import Protocol
from uuid import UUID


class CategoryReader(Protocol):
    """Outbound port: does this expense category exist for this user?

    A cap watches spending, so the flow is fixed to expenses — same shape as the reader
    `subscriptions` declares, and for the same reason: neither module may import the
    other's hexagon.
    """

    async def exists(self, user_id: UUID, category_id: str) -> bool: ...
