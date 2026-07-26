from typing import ClassVar

from src.shared.domain.errors import ConflictError, NotFoundError, ValidationError


class SubscriptionNotFoundError(NotFoundError):
    code: ClassVar[str] = "subscriptions.not_found"

    def __init__(self) -> None:
        super().__init__("Subscription not found")


class SubscriptionSourceNotFoundError(NotFoundError):
    code: ClassVar[str] = "subscriptions.source_not_found"

    def __init__(self, message: str = "Source not found") -> None:
        super().__init__(message)


class SubscriptionCategoryNotFoundError(ValidationError):
    code: ClassVar[str] = "subscriptions.category_not_found"

    def __init__(self) -> None:
        super().__init__("Category not found for this subscription")


class InvalidSubscriptionError(ValidationError):
    code: ClassVar[str] = "subscriptions.invalid"


class ChargeNotFoundError(NotFoundError):
    code: ClassVar[str] = "subscriptions.charge_not_found"

    def __init__(self) -> None:
        super().__init__("Charge not found")


class ChargeAlreadySettledError(ConflictError):
    """Confirming twice is a race, not a mistake: the answer is what already happened."""

    code: ClassVar[str] = "subscriptions.charge_already_settled"

    def __init__(self) -> None:
        super().__init__("This charge was already settled")
