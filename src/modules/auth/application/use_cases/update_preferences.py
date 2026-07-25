from dataclasses import dataclass

from src.modules.auth.application.dto.update_preferences import UpdatePreferencesInputDTO
from src.modules.auth.application.dto.user_profile import UserProfileDTO
from src.modules.auth.application.ports.auth_repository import AuthRepository
from src.modules.auth.domain.errors import InvalidCredentialsError


@dataclass
class UpdatePreferencesUseCase:
    auth_repository: AuthRepository

    async def execute(self, input_dto: UpdatePreferencesInputDTO) -> UserProfileDTO:
        user = await self.auth_repository.find_by_id(input_dto.user_id)
        if user is None:
            raise InvalidCredentialsError()

        preferences = user.preferences.patched(
            language=input_dto.language,
            currency=input_dto.currency,
            theme=input_dto.theme,
        )
        updated = user.with_preferences(preferences)
        await self.auth_repository.save(updated)

        return UserProfileDTO.from_domain(updated)
