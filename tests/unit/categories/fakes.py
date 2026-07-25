from uuid import UUID

from src.modules.categories.domain.entities.category import Category


class InMemoryCategoryRepository:
    """In-memory `CategoryRepository` for use-case unit tests (no Mongo)."""

    def __init__(self, *categories: Category) -> None:
        self.categories: list[Category] = list(categories)

    async def list_by_user(self, user_id: UUID) -> list[Category]:
        return [c for c in self.categories if c.user_id == user_id]

    async def find(self, user_id: UUID, category_id: str) -> Category | None:
        return next(
            (c for c in self.categories if c.id == category_id and c.user_id == user_id),
            None,
        )

    async def save(self, category: Category) -> None:
        self.categories = [c for c in self.categories if c.id != category.id]
        self.categories.append(category)

    async def delete(self, user_id: UUID, category_id: str) -> None:
        self.categories = [
            c for c in self.categories if not (c.id == category_id and c.user_id == user_id)
        ]
