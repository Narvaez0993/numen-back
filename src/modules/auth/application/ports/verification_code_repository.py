from typing import Protocol
from uuid import UUID

from src.modules.auth.domain.entities.email_verification_code import EmailVerificationCode


class VerificationCodeRepository(Protocol):
    """Outbound port: persistence of the active email verification code per user."""

    async def find_active_by_user(self, user_id: UUID) -> EmailVerificationCode | None: ...

    async def save(self, code: EmailVerificationCode) -> None: ...

    async def delete_by_user(self, user_id: UUID) -> None: ...
