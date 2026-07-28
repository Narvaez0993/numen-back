from typing import ClassVar

from src.shared.domain.errors import ForbiddenError, NotFoundError, ValidationError


class GoalNotFoundError(NotFoundError):
    code: ClassVar[str] = "goals.not_found"

    def __init__(self) -> None:
        super().__init__("Goal not found")


class GoalLimitReachedError(ForbiddenError):
    code: ClassVar[str] = "goals.limit_reached"

    def __init__(self) -> None:
        super().__init__("Active goal limit reached for your plan")


class GoalNotEmptyError(ValidationError):
    code: ClassVar[str] = "goals.not_empty"

    def __init__(self) -> None:
        # Archiving or deleting a pocket with money inside would hide real money the
        # app is supposed to show. Withdrawing first is one sheet away.
        super().__init__("Withdraw the money first: the pocket is not empty")


class GoalInsufficientError(ValidationError):
    code: ClassVar[str] = "goals.insufficient"

    def __init__(self) -> None:
        super().__init__("That withdrawal is more than the pocket holds")


class GoalArchivedError(ValidationError):
    code: ClassVar[str] = "goals.archived"

    def __init__(self) -> None:
        super().__init__("This goal is archived")


class InvalidGoalError(ValidationError):
    code: ClassVar[str] = "goals.invalid"
