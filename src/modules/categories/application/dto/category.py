from pydantic import BaseModel

from src.modules.categories.domain.entities.category import Category


class CategoryDTO(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    flow: str
    is_standard: bool

    @classmethod
    def from_domain(cls, category: Category) -> "CategoryDTO":
        return cls(
            id=category.id,
            name=category.name,
            icon=category.icon,
            color=category.color,
            flow=category.flow,
            is_standard=category.is_standard,
        )
