from dataclasses import dataclass

from src.modules.auth.application.dto.token import LogoutInputDTO
from src.modules.auth.application.ports.refresh_token_issuer import RefreshTokenIssuer
from src.modules.auth.application.ports.refresh_token_repository import RefreshTokenRepository
from src.shared.application.ports.clock import Clock


@dataclass
class LogoutUseCase:
    refresh_token_repository: RefreshTokenRepository
    refresh_token_issuer: RefreshTokenIssuer
    clock: Clock

    async def execute(self, input_dto: LogoutInputDTO) -> None:
        token_hash = self.refresh_token_issuer.hash(input_dto.refresh_token)
        stored = await self.refresh_token_repository.find_by_hash(token_hash)
        if stored is None:
            return
        await self.refresh_token_repository.revoke_family(stored.family_id, self.clock.now())
