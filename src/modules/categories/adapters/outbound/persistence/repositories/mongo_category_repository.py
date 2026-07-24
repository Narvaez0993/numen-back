from uuid import UUID

from src.modules.categories.adapters.outbound.persistence.documents.category_document import (
    CategoryDocument,
)
from src.modules.categories.adapters.outbound.persistence.mappers.category_mapper import (
    CategoryMapper,
)
from src.modules.categories.domain.entities.category import Category


class MongoCategoryRepository:
    """Beanie/Mongo implementation of `CategoryRepository` (custom categories).

    All queries are prefixed by `user_id`, served by the compound index on
    `(user_id, flow, name)` declared in `CategoryDocument`.
    """

    async def list_by_user(self, user_id: UUID) -> list[Category]:
        docs = await CategoryDocument.find(CategoryDocument.user_id == str(user_id)).to_list()
        return [CategoryMapper.to_domain(doc) for doc in docs]

    async def find(self, user_id: UUID, category_id: str) -> Category | None:
        doc = await CategoryDocument.find_one(
            CategoryDocument.id == category_id,
            CategoryDocument.user_id == str(user_id),
        )
        return CategoryMapper.to_domain(doc) if doc else None

    async def save(self, category: Category) -> None:
        existing = await CategoryDocument.get(category.id)
        if existing is None:
            await CategoryMapper.to_document(category).insert()
            return
        existing.name = category.name
        existing.icon = category.icon
        existing.color = category.color
        existing.flow = category.flow
        await existing.save()

    async def delete(self, user_id: UUID, category_id: str) -> None:
        doc = await CategoryDocument.find_one(
            CategoryDocument.id == category_id,
            CategoryDocument.user_id == str(user_id),
        )
        if doc is not None:
            await doc.delete()
