from dataclasses import dataclass

from src.modules.auth.application.dto.update_display_name import (
    UpdateDisplayNameInputDTO,
)
from src.modules.auth.application.dto.user_profile import UserProfileDTO
from src.modules.auth.application.ports.auth_repository import AuthRepository
from src.modules.auth.domain.errors import InvalidCredentialsError


@dataclass
class UpdateDisplayNameUseCase:
    auth_repository: AuthRepository

    async def execute(self, input_dto: UpdateDisplayNameInputDTO) -> UserProfileDTO:
        user = await self.auth_repository.find_by_id(input_dto.user_id)
        if user is None:
            raise InvalidCredentialsError()

        updated = user.with_display_name(input_dto.display_name.strip())
        await self.auth_repository.save(updated)

        return UserProfileDTO.from_domain(updated)
