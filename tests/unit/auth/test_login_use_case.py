import pytest

from src.modules.auth.application.dto.login import LoginInputDTO
from src.modules.auth.application.use_cases.login import LoginUseCase
from src.modules.auth.domain.errors import EmailNotVerifiedError, InvalidCredentialsError
from tests.unit.auth.fakes import (
    FakePasswordHasher,
    FixedClock,
    InMemoryAuthRepository,
    InMemoryRefreshTokenRepository,
    make_session_issuer,
    make_user,
)


def _use_case(repo: InMemoryAuthRepository) -> LoginUseCase:
    refresh_repo = InMemoryRefreshTokenRepository()
    return LoginUseCase(
        auth_repository=repo,
        password_hasher=FakePasswordHasher(),
        session_issuer=make_session_issuer(FixedClock(), refresh_repo),
    )


@pytest.mark.asyncio
async def test_login_returns_session_on_valid_credentials() -> None:
    result = await _use_case(
        InMemoryAuthRepository(make_user(verified=True))
    ).execute(LoginInputDTO(email="demo@numen.app", password="demo1234"))

    assert result.email == "demo@numen.app"
    assert result.access_token.startswith("access-")
    assert result.refresh_token != ""


@pytest.mark.asyncio
async def test_login_rejects_unverified_email() -> None:
    with pytest.raises(EmailNotVerifiedError):
        await _use_case(
            InMemoryAuthRepository(make_user(verified=False))
        ).execute(LoginInputDTO(email="demo@numen.app", password="demo1234"))


@pytest.mark.asyncio
async def test_login_rejects_wrong_password() -> None:
    with pytest.raises(InvalidCredentialsError):
        await _use_case(
            InMemoryAuthRepository(make_user(verified=True))
        ).execute(LoginInputDTO(email="demo@numen.app", password="wrong"))


@pytest.mark.asyncio
async def test_login_rejects_unknown_email() -> None:
    with pytest.raises(InvalidCredentialsError):
        await _use_case(InMemoryAuthRepository()).execute(
            LoginInputDTO(email="ghost@numen.app", password="whatever")
        )
