from datetime import timedelta

import pytest

from src.modules.auth.application.dto.token import RefreshInputDTO
from src.modules.auth.application.use_cases.refresh import RefreshUseCase
from src.modules.auth.domain.entities.refresh_token import RefreshToken
from src.modules.auth.domain.errors import (
    InvalidRefreshTokenError,
    RefreshTokenReusedError,
)
from tests.unit.auth.fakes import (
    FakeRefreshTokenIssuer,
    FixedClock,
    InMemoryAuthRepository,
    InMemoryRefreshTokenRepository,
    make_session_issuer,
    make_user,
)


@pytest.mark.asyncio
async def test_refresh_rotates_and_revokes_previous() -> None:
    user = make_user(verified=True)
    clock = FixedClock()
    refresh_repo = InMemoryRefreshTokenRepository()
    session_issuer = make_session_issuer(clock, refresh_repo)
    first = await session_issuer.issue(user)

    use_case = RefreshUseCase(
        auth_repository=InMemoryAuthRepository(user),
        refresh_token_repository=refresh_repo,
        refresh_token_issuer=FakeRefreshTokenIssuer(),
        session_issuer=session_issuer,
        clock=clock,
    )
    rotated = await use_case.execute(RefreshInputDTO(refresh_token=first.refresh_token))

    assert rotated.refresh_token != first.refresh_token
    previous = await refresh_repo.find_by_hash(f"h:{first.refresh_token}")
    assert previous is not None
    assert previous.is_revoked()


@pytest.mark.asyncio
async def test_refresh_reuse_detected_and_family_revoked() -> None:
    user = make_user(verified=True)
    clock = FixedClock()
    refresh_repo = InMemoryRefreshTokenRepository()
    session_issuer = make_session_issuer(clock, refresh_repo)
    first = await session_issuer.issue(user)

    use_case = RefreshUseCase(
        auth_repository=InMemoryAuthRepository(user),
        refresh_token_repository=refresh_repo,
        refresh_token_issuer=FakeRefreshTokenIssuer(),
        session_issuer=session_issuer,
        clock=clock,
    )
    rotated = await use_case.execute(RefreshInputDTO(refresh_token=first.refresh_token))

    with pytest.raises(RefreshTokenReusedError):
        await use_case.execute(RefreshInputDTO(refresh_token=first.refresh_token))

    successor = await refresh_repo.find_by_hash(f"h:{rotated.refresh_token}")
    assert successor is not None
    assert successor.is_revoked()


@pytest.mark.asyncio
async def test_refresh_rejects_expired_token() -> None:
    user = make_user(verified=True)
    clock = FixedClock()
    refresh_repo = InMemoryRefreshTokenRepository()
    await refresh_repo.save(
        RefreshToken.issue(
            user_id=user.id,
            token_hash="h:stale",
            expires_at=clock.now() - timedelta(seconds=1),
            created_at=clock.now() - timedelta(days=31),
        )
    )

    use_case = RefreshUseCase(
        auth_repository=InMemoryAuthRepository(user),
        refresh_token_repository=refresh_repo,
        refresh_token_issuer=FakeRefreshTokenIssuer(),
        session_issuer=make_session_issuer(clock, refresh_repo),
        clock=clock,
    )

    with pytest.raises(InvalidRefreshTokenError):
        await use_case.execute(RefreshInputDTO(refresh_token="stale"))


@pytest.mark.asyncio
async def test_refresh_rejects_unknown_token() -> None:
    user = make_user(verified=True)
    clock = FixedClock()
    refresh_repo = InMemoryRefreshTokenRepository()
    use_case = RefreshUseCase(
        auth_repository=InMemoryAuthRepository(user),
        refresh_token_repository=refresh_repo,
        refresh_token_issuer=FakeRefreshTokenIssuer(),
        session_issuer=make_session_issuer(clock, refresh_repo),
        clock=clock,
    )

    with pytest.raises(InvalidRefreshTokenError):
        await use_case.execute(RefreshInputDTO(refresh_token="never-issued"))
