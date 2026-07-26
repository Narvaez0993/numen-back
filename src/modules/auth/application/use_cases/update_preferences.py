from dataclasses import dataclass

from src.modules.auth.application.dto.update_preferences import UpdatePreferencesInputDTO
from src.modules.auth.application.dto.user_profile import UserProfileDTO
from src.modules.auth.application.ports.auth_repository import AuthRepository
from src.modules.auth.application.ports.currency_scope import CurrencyScope
from src.modules.auth.domain.errors import (
    CurrencyChangeBlockedError,
    InvalidCredentialsError,
)
from src.shared.application.ports.unit_of_work import UnitOfWork


@dataclass
class UpdatePreferencesUseCase:
    """Patches the user's settings. Language and theme are free; the **currency is
    not**, because every stored amount is denominated in its minor unit.

    Changing it is treated as a **correction, never a conversion** (there are no
    exchange rates here): the user's sources and forecasts are re-labelled so they
    stay usable, and it is refused outright once there is a history that a re-label
    would misread. Without this, changing the currency left the user's own accounts
    unusable — every movement and subscription on them was rejected for a currency
    mismatch nobody could see.
    """

    auth_repository: AuthRepository
    currency_scope: CurrencyScope
    unit_of_work: UnitOfWork

    async def execute(self, input_dto: UpdatePreferencesInputDTO) -> UserProfileDTO:
        user = await self.auth_repository.find_by_id(input_dto.user_id)
        if user is None:
            raise InvalidCredentialsError()

        preferences = user.preferences.patched(
            language=input_dto.language,
            currency=input_dto.currency,
            theme=input_dto.theme,
        )
        currency_changed = preferences.currency != user.preferences.currency
        if currency_changed and await self.currency_scope.has_history(input_dto.user_id):
            raise CurrencyChangeBlockedError(user.preferences.currency)

        updated = user.with_preferences(preferences)

        async def apply() -> None:
            await self.auth_repository.save(updated)
            if currency_changed:
                await self.currency_scope.restamp(input_dto.user_id, preferences.currency)

        # One unit: a saved preference whose sources kept the old currency is exactly
        # the broken state this use case exists to prevent.
        await self.unit_of_work.atomic(apply)

        return UserProfileDTO.from_domain(updated)
