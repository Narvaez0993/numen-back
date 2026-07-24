from dataclasses import dataclass

from src.modules.auth.application.dto.session import AuthSessionDTO
from src.modules.auth.application.dto.verify_email import VerifyEmailInputDTO
from src.modules.auth.application.ports.auth_repository import AuthRepository
from src.modules.auth.application.ports.verification_code_repository import (
    VerificationCodeRepository,
)
from src.modules.auth.application.services.session_issuer import SessionIssuer
from src.modules.auth.domain.errors import (
    VerificationAttemptsExceededError,
    VerificationCodeExpiredError,
    VerificationCodeInvalidError,
)
from src.modules.auth.domain.value_objects.email import Email
from src.shared.application.ports.clock import Clock


@dataclass
class VerifyEmailUseCase:
    auth_repository: AuthRepository
    verification_code_repository: VerificationCodeRepository
    session_issuer: SessionIssuer
    clock: Clock
    max_attempts: int

    async def execute(self, input_dto: VerifyEmailInputDTO) -> AuthSessionDTO:
        email = Email.create(input_dto.email)
        user = await self.auth_repository.find_by_email(email)
        if user is None:
            raise VerificationCodeInvalidError()

        code = await self.verification_code_repository.find_active_by_user(user.id)
        if code is None:
            raise VerificationCodeInvalidError()

        if code.is_expired(self.clock.now()):
            raise VerificationCodeExpiredError()

        if code.attempts_exhausted(self.max_attempts):
            raise VerificationAttemptsExceededError()

        if code.code != input_dto.code:
            await self.verification_code_repository.save(code.with_failed_attempt())
            raise VerificationCodeInvalidError()

        await self.auth_repository.save(user.verified())
        await self.verification_code_repository.delete_by_user(user.id)
        return await self.session_issuer.issue(user.verified())
