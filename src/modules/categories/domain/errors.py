from typing import ClassVar

from src.shared.domain.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


class CategoryNotFoundError(NotFoundError):
    code: ClassVar[str] = "categories.not_found"

    def __init__(self) -> None:
        super().__init__("Category not found")


class CategoryNameTakenError(ConflictError):
    code: ClassVar[str] = "categories.name_taken"

    def __init__(self) -> None:
        super().__init__("A category with that name already exists")


class CategoryLimitReachedError(ForbiddenError):
    code: ClassVar[str] = "categories.limit_reached"

    def __init__(self) -> None:
        super().__init__("Custom category limit reached for your plan")


class InvalidCategoryError(ValidationError):
    code: ClassVar[str] = "categories.invalid"
