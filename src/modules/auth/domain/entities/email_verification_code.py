from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class EmailVerificationCode:
    """A one-time code sent to confirm ownership of an email address.

    Stored in plaintext by design (dev phase): its only reader is the database
    owner or the dev email adapter's log. State and rules live here; matching
    and generation are handled by the use case through ports.
    """

    user_id: UUID
    code: str
    expires_at: datetime
    attempts: int
    resend_available_at: datetime
    created_at: datetime

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def attempts_exhausted(self, max_attempts: int) -> bool:
        return self.attempts >= max_attempts

    def can_resend(self, now: datetime) -> bool:
        return now >= self.resend_available_at

    def with_failed_attempt(self) -> "EmailVerificationCode":
        return replace(self, attempts=self.attempts + 1)
