from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from src.modules.auth.application.dto.session import AuthSessionDTO
from src.modules.auth.application.ports.refresh_token_issuer import RefreshTokenIssuer
from src.modules.auth.application.ports.refresh_token_repository import RefreshTokenRepository
from src.modules.auth.application.ports.token_service import TokenService
from src.modules.auth.domain.entities.refresh_token import RefreshToken
from src.modules.auth.domain.entities.user import User
from src.shared.application.ports.clock import Clock


@dataclass
class SessionIssuer:
    """Mints an access + refresh pair for a user and persists the refresh token.

    Shared by login, email verification and refresh rotation. Passing an
    existing `family_id` keeps a rotated token within its lineage; omitting it
    starts a new family (a fresh login).
    """

    token_service: TokenService
    refresh_token_issuer: RefreshTokenIssuer
    refresh_token_repository: RefreshTokenRepository
    clock: Clock
    refresh_ttl_days: int

    async def issue(self, user: User, family_id: UUID | None = None) -> AuthSessionDTO:
        now = self.clock.now()
        raw_token, token_hash = self.refresh_token_issuer.issue()
        refresh_token = RefreshToken.issue(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(days=self.refresh_ttl_days),
            created_at=now,
            family_id=family_id,
        )
        await self.refresh_token_repository.save(refresh_token)

        access_token = self.token_service.issue_access_token(
            user_id=user.id,
            tier=user.tier,
        )
        return AuthSessionDTO(
            user_id=str(user.id),
            email=user.email.value,
            display_name=user.display_name,
            tier=user.tier,
            language=user.preferences.language,
            currency=user.preferences.currency,
            theme=user.preferences.theme,
            access_token=access_token,
            refresh_token=raw_token,
        )
