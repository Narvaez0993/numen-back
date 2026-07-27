from typing import ClassVar

from src.shared.domain.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


class BudgetNotFoundError(NotFoundError):
    code: ClassVar[str] = "budgets.not_found"

    def __init__(self) -> None:
        super().__init__("Budget not found")


class BudgetAlreadyExistsError(ConflictError):
    code: ClassVar[str] = "budgets.already_exists"

    def __init__(self) -> None:
        # One global cap per user, one cap per category: a second one is an edit of the
        # first, not a new row. The unique index says the same thing in the store.
        super().__init__("You already have a cap for that")


class BudgetLimitReachedError(ForbiddenError):
    code: ClassVar[str] = "budgets.limit_reached"

    def __init__(self) -> None:
        super().__init__("Category cap limit reached for your plan")


class BudgetCategoryNotFoundError(ValidationError):
    code: ClassVar[str] = "budgets.unknown_category"

    def __init__(self) -> None:
        # Its own code, not a generic `invalid`: the client can point at the field, and
        # it is the one failure here that a stale catalog can cause on its own.
        super().__init__("That expense category does not exist")


class InvalidBudgetError(ValidationError):
    code: ClassVar[str] = "budgets.invalid"
