from dataclasses import dataclass
from datetime import timedelta

from src.modules.auth.application.dto.register import RegisterInputDTO, RegisterOutputDTO
from src.modules.auth.application.ports.auth_repository import AuthRepository
from src.modules.auth.application.ports.code_generator import CodeGenerator
from src.modules.auth.application.ports.email_sender import EmailSender
from src.modules.auth.application.ports.password_hasher import PasswordHasher
from src.modules.auth.application.ports.verification_code_repository import (
    VerificationCodeRepository,
)
from src.modules.auth.domain.entities.email_verification_code import EmailVerificationCode
from src.modules.auth.domain.entities.user import User
from src.modules.auth.domain.errors import UserAlreadyExistsError, WeakPasswordError
from src.modules.auth.domain.value_objects.email import Email
from src.shared.application.ports.clock import Clock

_MIN_PASSWORD_LENGTH = 8


@dataclass
class RegisterUseCase:
    auth_repository: AuthRepository
    password_hasher: PasswordHasher
    code_generator: CodeGenerator
    verification_code_repository: VerificationCodeRepository
    email_sender: EmailSender
    clock: Clock
    code_ttl_minutes: int
    resend_cooldown_seconds: int

    async def execute(self, input_dto: RegisterInputDTO) -> RegisterOutputDTO:
        if len(input_dto.password) < _MIN_PASSWORD_LENGTH:
            raise WeakPasswordError()

        email = Email.create(input_dto.email)
        existing = await self.auth_repository.find_by_email(email)
        if existing is not None:
            raise UserAlreadyExistsError(f"Email already registered: {email.value}")

        now = self.clock.now()
        hashed = self.password_hasher.hash(input_dto.password)
        user = User.new(
            email=email,
            display_name=input_dto.display_name.strip(),
            hashed_password=hashed,
            created_at=now,
        )
        await self.auth_repository.save(user)

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

        return RegisterOutputDTO(
            user_id=str(user.id),
            email=user.email.value,
            display_name=user.display_name,
            tier=user.tier,
            email_verified=user.email_verified,
        )
