import pytest

from src.modules.auth.application.dto.token import LogoutInputDTO
from src.modules.auth.application.use_cases.logout import LogoutUseCase
from tests.unit.auth.fakes import (
    FakeRefreshTokenIssuer,
    FixedClock,
    InMemoryRefreshTokenRepository,
    make_session_issuer,
    make_user,
)


@pytest.mark.asyncio
async def test_logout_revokes_the_session_family() -> None:
    user = make_user(verified=True)
    clock = FixedClock()
    refresh_repo = InMemoryRefreshTokenRepository()
    session = await make_session_issuer(clock, refresh_repo).issue(user)

    use_case = LogoutUseCase(
        refresh_token_repository=refresh_repo,
        refresh_token_issuer=FakeRefreshTokenIssuer(),
        clock=clock,
    )
    await use_case.execute(LogoutInputDTO(refresh_token=session.refresh_token))

    stored = await refresh_repo.find_by_hash(f"h:{session.refresh_token}")
    assert stored is not None
    assert stored.is_revoked()


@pytest.mark.asyncio
async def test_logout_is_silent_for_unknown_token() -> None:
    use_case = LogoutUseCase(
        refresh_token_repository=InMemoryRefreshTokenRepository(),
        refresh_token_issuer=FakeRefreshTokenIssuer(),
        clock=FixedClock(),
    )
    await use_case.execute(LogoutInputDTO(refresh_token="unknown"))
