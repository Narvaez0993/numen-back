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


class SubscriptionSourceCurrencyMismatchError(ValidationError):
    """Same as movements': the account and the home currency disagree, and no form
    field the user can edit will fix it — so it says what is actually wrong."""

    code: ClassVar[str] = "subscriptions.source_currency_mismatch"

    def __init__(self, source_currency: str, user_currency: str) -> None:
        super().__init__(
            f"This source is in {source_currency} and your currency is {user_currency}"
        )
