from typing import ClassVar


class DomainError(Exception):
    """Base for any error raised by the domain or application layer.

    Subclasses define `code` (machine-readable) and `http_status` (default
    mapping when the global exception handler converts to HTTP).
    """

    code: ClassVar[str] = "domain.error"
    http_status: ClassVar[int] = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    code: ClassVar[str] = "common.not_found"
    http_status: ClassVar[int] = 404


class ConflictError(DomainError):
    code: ClassVar[str] = "common.conflict"
    http_status: ClassVar[int] = 409


class UnauthorizedError(DomainError):
    code: ClassVar[str] = "common.unauthorized"
    http_status: ClassVar[int] = 401


class ForbiddenError(DomainError):
    code: ClassVar[str] = "common.forbidden"
    http_status: ClassVar[int] = 403


class ValidationError(DomainError):
    code: ClassVar[str] = "common.validation"
    http_status: ClassVar[int] = 422


class QuotaExceededError(DomainError):
    code: ClassVar[str] = "common.quota_exceeded"
    http_status: ClassVar[int] = 429
