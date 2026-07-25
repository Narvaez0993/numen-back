from typing import ClassVar

from src.shared.domain.errors import ForbiddenError, NotFoundError, ValidationError


class AccountNotFoundError(NotFoundError):
    code: ClassVar[str] = "accounts.not_found"

    def __init__(self, message: str = "Account not found") -> None:
        super().__init__(message)


class CreditCardNotFoundError(AccountNotFoundError):
    """Same code as accounts: from the client's side both are "the source is gone"."""

    def __init__(self) -> None:
        super().__init__("Credit card not found")


class AccountLimitReachedError(ForbiddenError):
    code: ClassVar[str] = "accounts.limit_reached"

    def __init__(self) -> None:
        super().__init__("Account limit reached for your plan")


class CreditCardLimitReachedError(ForbiddenError):
    code: ClassVar[str] = "accounts.card_limit_reached"

    def __init__(self) -> None:
        super().__init__("Credit card limit reached for your plan")


class InvalidAccountError(ValidationError):
    code: ClassVar[str] = "accounts.invalid"
