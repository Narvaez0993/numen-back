from dataclasses import dataclass

from src.modules.auth.application.dto.register import RegisterInputDTO, RegisterOutputDTO
from src.modules.auth.application.ports.auth_repository import AuthRepository
from src.modules.auth.application.ports.password_hasher import PasswordHasher
from src.modules.auth.application.ports.token_service import TokenService
from src.modules.auth.domain.entities.user import User
from src.modules.auth.domain.errors import UserAlreadyExistsError, WeakPasswordError
from src.modules.auth.domain.value_objects.email import Email

_MIN_PASSWORD_LENGTH = 8


@dataclass
class RegisterUseCase:
    auth_repository: AuthRepository
    password_hasher: PasswordHasher
    token_service: TokenService

    async def execute(self, input_dto: RegisterInputDTO) -> RegisterOutputDTO:
        if len(input_dto.password) < _MIN_PASSWORD_LENGTH:
            raise WeakPasswordError()

        email = Email.create(input_dto.email)
        existing = await self.auth_repository.find_by_email(email)
        if existing is not None:
            raise UserAlreadyExistsError(f"Email already registered: {email.value}")

        hashed = self.password_hasher.hash(input_dto.password)
        user = User.new(
            email=email,
            display_name=input_dto.display_name.strip(),
            hashed_password=hashed,
        )
        await self.auth_repository.save(user)

        access_token = self.token_service.issue_access_token(
            user_id=user.id,
            tier=user.tier,
        )
        return RegisterOutputDTO(
            user_id=str(user.id),
            email=user.email.value,
            display_name=user.display_name,
            tier=user.tier,
            access_token=access_token,
        )
