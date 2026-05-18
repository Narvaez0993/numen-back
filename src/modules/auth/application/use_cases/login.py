from dataclasses import dataclass

from src.modules.auth.application.dto.login import LoginInputDTO, LoginOutputDTO
from src.modules.auth.application.ports.auth_repository import AuthRepository
from src.modules.auth.application.ports.password_hasher import PasswordHasher
from src.modules.auth.application.ports.token_service import TokenService
from src.modules.auth.domain.errors import InvalidCredentialsError
from src.modules.auth.domain.value_objects.email import Email


@dataclass
class LoginUseCase:
    auth_repository: AuthRepository
    password_hasher: PasswordHasher
    token_service: TokenService

    async def execute(self, input_dto: LoginInputDTO) -> LoginOutputDTO:
        email = Email.create(input_dto.email)
        user = await self.auth_repository.find_by_email(email)
        if user is None or not self.password_hasher.verify(
            user.hashed_password, input_dto.password
        ):
            raise InvalidCredentialsError()

        access_token = self.token_service.issue_access_token(
            user_id=user.id,
            tier=user.tier,
        )
        return LoginOutputDTO(
            user_id=str(user.id),
            email=user.email.value,
            display_name=user.display_name,
            tier=user.tier,
            access_token=access_token,
        )
