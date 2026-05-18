from typing import ClassVar

from src.shared.domain.errors import ConflictError, UnauthorizedError, ValidationError


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
