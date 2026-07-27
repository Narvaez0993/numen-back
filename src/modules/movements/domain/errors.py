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


class SourceCurrencyMismatchError(ValidationError):
    """The source is denominated in another currency than the caller's.

    Its own code instead of the generic `movements.invalid` because it is the one
    validation failure the user **cannot fix from the form** — it means their account
    and their home currency disagree, and the message has to say so.
    """

    code: ClassVar[str] = "movements.source_currency_mismatch"

    def __init__(self, source_currency: str, user_currency: str) -> None:
        super().__init__(
            f"This source is in {source_currency} and your currency is {user_currency}"
        )
