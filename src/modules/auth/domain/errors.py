from typing import ClassVar

from src.shared.domain.errors import (
    ConflictError,
    ForbiddenError,
    QuotaExceededError,
    UnauthorizedError,
    ValidationError,
)


class InvalidCredentialsError(UnauthorizedError):
    code: ClassVar[str] = "auth.invalid_credentials"

    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class UserAlreadyExistsError(ConflictError):
    code: ClassVar[str] = "auth.user_already_exists"


class WeakPasswordError(ValidationError):
    code: ClassVar[str] = "auth.weak_password"

    def __init__(self, message: str = "Password must be at least 8 characters") -> None:
        super().__init__(message)


class EmailNotVerifiedError(ForbiddenError):
    code: ClassVar[str] = "auth.email_not_verified"

    def __init__(self) -> None:
        super().__init__("Email address is not verified")


class VerificationCodeInvalidError(ValidationError):
    code: ClassVar[str] = "auth.verification_code_invalid"

    def __init__(self) -> None:
        super().__init__("Verification code is invalid")


class VerificationCodeExpiredError(ValidationError):
    code: ClassVar[str] = "auth.verification_code_expired"

    def __init__(self) -> None:
        super().__init__("Verification code has expired")


class VerificationAttemptsExceededError(QuotaExceededError):
    code: ClassVar[str] = "auth.verification_attempts_exceeded"

    def __init__(self) -> None:
        super().__init__("Too many verification attempts; request a new code")


class ResendCooldownError(QuotaExceededError):
    code: ClassVar[str] = "auth.resend_cooldown"

    def __init__(self) -> None:
        super().__init__("A code was requested recently; wait before resending")


class InvalidRefreshTokenError(UnauthorizedError):
    code: ClassVar[str] = "auth.invalid_refresh_token"

    def __init__(self) -> None:
        super().__init__("Refresh token is invalid or expired")


class RefreshTokenReusedError(UnauthorizedError):
    code: ClassVar[str] = "auth.refresh_token_reused"

    def __init__(self) -> None:
        super().__init__("Refresh token was already used; session revoked")


class CurrencyChangeBlockedError(ConflictError):
    """The home currency cannot change once money has been registered.

    Amounts are stored in the currency's minor unit, and the exponent differs (COP 0,
    USD 2), so re-labelling a history would move every decimal point — a silent 100x
    error on data the user trusts. Blocking is the honest answer; the way out is to
    start over, not to have the app guess.
    """

    code: ClassVar[str] = "auth.currency_change_blocked"

    def __init__(self, current: str) -> None:
        super().__init__(
            f"Your data is registered in {current}. "
            "Changing the home currency would re-label amounts you already saved."
        )
