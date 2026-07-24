from typing import Protocol
from uuid import UUID

from src.modules.categories.domain.entities.category import Category


class CategoryRepository(Protocol):
    """Outbound port: persistence of custom `Category` aggregates (per user).

    Standard categories live in the code catalog and are never persisted here.
    The custom set per user is small (bounded by the plan), so callers list it
    to both count (capacity gate) and dedupe names in one indexed query.
    """

    async def list_by_user(self, user_id: UUID) -> list[Category]: ...

    async def find(self, user_id: UUID, category_id: str) -> Category | None: ...

    async def save(self, category: Category) -> None: ...

    async def delete(self, user_id: UUID, category_id: str) -> None: ...
