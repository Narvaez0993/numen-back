from typing import ClassVar

from src.shared.domain.errors import NotFoundError, ValidationError


class MovementNotFoundError(NotFoundError):
    code: ClassVar[str] = "movements.not_found"

    def __init__(self) -> None:
        super().__init__("Movement not found")


class SourceNotFoundError(NotFoundError):
    code: ClassVar[str] = "movements.source_not_found"

    def __init__(self, message: str = "Source not found") -> None:
        super().__init__(message)


class MovementCategoryNotFoundError(ValidationError):
    code: ClassVar[str] = "movements.category_not_found"

    def __init__(self) -> None:
        super().__init__("Category not found for this movement")


class InvalidMovementError(ValidationError):
    code: ClassVar[str] = "movements.invalid"
