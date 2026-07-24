from dataclasses import dataclass

from src.modules.auth.application.dto.login import LoginInputDTO
from src.modules.auth.application.dto.session import AuthSessionDTO
from src.modules.auth.application.ports.auth_repository import AuthRepository
from src.modules.auth.application.ports.password_hasher import PasswordHasher
from src.modules.auth.application.services.session_issuer import SessionIssuer
from src.modules.auth.domain.errors import EmailNotVerifiedError, InvalidCredentialsError
from src.modules.auth.domain.value_objects.email import Email


@dataclass
class LoginUseCase:
    auth_repository: AuthRepository
    password_hasher: PasswordHasher
    session_issuer: SessionIssuer

    async def execute(self, input_dto: LoginInputDTO) -> AuthSessionDTO:
        email = Email.create(input_dto.email)
        user = await self.auth_repository.find_by_email(email)
        if user is None or not self.password_hasher.verify(
            user.hashed_password, input_dto.password
        ):
            raise InvalidCredentialsError()

        if not user.email_verified:
            raise EmailNotVerifiedError()

        return await self.session_issuer.issue(user)
