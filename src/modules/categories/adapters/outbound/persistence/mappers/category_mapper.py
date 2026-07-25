from typing import cast
from uuid import UUID

from src.modules.categories.adapters.outbound.persistence.documents.category_document import (
    CategoryDocument,
)
from src.modules.categories.domain.entities.category import Category, CategoryFlow


class CategoryMapper:
    @staticmethod
    def to_domain(doc: CategoryDocument) -> Category:
        return Category(
            id=doc.id,
            user_id=UUID(doc.user_id),
            name=doc.name,
            icon=doc.icon,
            color=doc.color,
            flow=cast(CategoryFlow, doc.flow),
            is_standard=False,
        )

    @staticmethod
    def to_document(category: Category) -> CategoryDocument:
        return CategoryDocument(
            id=category.id,
            user_id=str(category.user_id),
            name=category.name,
            icon=category.icon,
            color=category.color,
            flow=category.flow,
        )
