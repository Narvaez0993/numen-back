from dataclasses import dataclass
from datetime import timedelta

from src.modules.auth.application.dto.resend_code import ResendCodeInputDTO
from src.modules.auth.application.ports.auth_repository import AuthRepository
from src.modules.auth.application.ports.code_generator import CodeGenerator
from src.modules.auth.application.ports.email_sender import EmailSender
from src.modules.auth.application.ports.verification_code_repository import (
    VerificationCodeRepository,
)
from src.modules.auth.domain.entities.email_verification_code import EmailVerificationCode
from src.modules.auth.domain.errors import ResendCooldownError, VerificationCodeInvalidError
from src.modules.auth.domain.value_objects.email import Email
from src.shared.application.ports.clock import Clock


@dataclass
class ResendCodeUseCase:
    auth_repository: AuthRepository
    verification_code_repository: VerificationCodeRepository
    code_generator: CodeGenerator
    email_sender: EmailSender
    clock: Clock
    code_ttl_minutes: int
    resend_cooldown_seconds: int

    async def execute(self, input_dto: ResendCodeInputDTO) -> None:
        email = Email.create(input_dto.email)
        user = await self.auth_repository.find_by_email(email)
        if user is None or user.email_verified:
            raise VerificationCodeInvalidError()

        now = self.clock.now()
        existing = await self.verification_code_repository.find_active_by_user(user.id)
        if existing is not None and not existing.can_resend(now):
            raise ResendCooldownError()

        code = EmailVerificationCode(
            user_id=user.id,
            code=self.code_generator.generate(),
            expires_at=now + timedelta(minutes=self.code_ttl_minutes),
            attempts=0,
            resend_available_at=now + timedelta(seconds=self.resend_cooldown_seconds),
            created_at=now,
        )
        await self.verification_code_repository.save(code)
        await self.email_sender.send_verification_code(user.email.value, code.code)
