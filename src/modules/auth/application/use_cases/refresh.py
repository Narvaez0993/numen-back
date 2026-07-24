from dataclasses import dataclass

from src.modules.auth.application.dto.session import AuthSessionDTO
from src.modules.auth.application.dto.token import RefreshInputDTO
from src.modules.auth.application.ports.auth_repository import AuthRepository
from src.modules.auth.application.ports.refresh_token_issuer import RefreshTokenIssuer
from src.modules.auth.application.ports.refresh_token_repository import RefreshTokenRepository
from src.modules.auth.application.services.session_issuer import SessionIssuer
from src.modules.auth.domain.errors import (
    InvalidRefreshTokenError,
    RefreshTokenReusedError,
)
from src.shared.application.ports.clock import Clock


@dataclass
class RefreshUseCase:
    auth_repository: AuthRepository
    refresh_token_repository: RefreshTokenRepository
    refresh_token_issuer: RefreshTokenIssuer
    session_issuer: SessionIssuer
    clock: Clock

    async def execute(self, input_dto: RefreshInputDTO) -> AuthSessionDTO:
        now = self.clock.now()
        token_hash = self.refresh_token_issuer.hash(input_dto.refresh_token)
        stored = await self.refresh_token_repository.find_by_hash(token_hash)

        if stored is None:
            raise InvalidRefreshTokenError()

        if stored.is_revoked():
            await self.refresh_token_repository.revoke_family(stored.family_id, now)
            raise RefreshTokenReusedError()

        if not stored.is_active(now):
            raise InvalidRefreshTokenError()

        user = await self.auth_repository.find_by_id(stored.user_id)
        if user is None:
            raise InvalidRefreshTokenError()

        await self.refresh_token_repository.save(stored.revoke(now))
        return await self.session_issuer.issue(user, family_id=stored.family_id)
