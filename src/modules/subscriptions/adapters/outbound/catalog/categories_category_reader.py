from dataclasses import dataclass
from uuid import UUID

from src.modules.categories.application.ports.category_repository import CategoryRepository
from src.modules.categories.domain.standard_catalog import STANDARD_CATEGORIES

_EXPENSE = "expense"


@dataclass
class CategoriesCategoryReader:
    """`CategoryReader` backed by the categories module.

    Resolves against the code catalog first (no query for the standard ones — the
    default for a subscription, `subs`, is one of them) and only reads the user's
    custom set when the id is not standard.
    """

    category_repository: CategoryRepository

    async def exists(self, user_id: UUID, category_id: str) -> bool:
        for category in STANDARD_CATEGORIES:
            if category.id == category_id:
                return category.flow == _EXPENSE

        customs = await self.category_repository.list_by_user(user_id)
        return any(c.id == category_id and c.flow == _EXPENSE for c in customs)
