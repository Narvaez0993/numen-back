from typing import Protocol
from uuid import UUID


class CategoryReader(Protocol):
    """Outbound port: does this expense category exist for this user?

    Subscriptions only ever file expenses, so the flow is fixed — the port does not
    take one, unlike movements' `CategoryLookup`.
    """

    async def exists(self, user_id: UUID, category_id: str) -> bool: ...
