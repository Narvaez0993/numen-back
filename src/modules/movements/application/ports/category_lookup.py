from typing import Protocol
from uuid import UUID


class CategoryLookup(Protocol):
    """Outbound port: does this category exist for this user, with this flow?

    Same seam as `SourceLedger` — movements validates the reference without
    knowing that categories come from a code catalog plus the user's custom ones.
    `flow` is `'expense'` or `'income'`, so a movement can't be filed under a
    category of the wrong kind.
    """

    async def exists(self, user_id: UUID, category_id: str, flow: str) -> bool: ...
