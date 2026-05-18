from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.modules.auth.application.dto.login import LoginInputDTO
from src.modules.auth.application.use_cases.login import LoginUseCase
from src.modules.auth.domain.entities.user import User
from src.modules.auth.domain.errors import InvalidCredentialsError
from src.modules.auth.domain.value_objects.email import Email
from src.modules.auth.domain.value_objects.hashed_password import HashedPassword


class _InMemoryAuthRepository:
    def __init__(self, user: User | None = None) -> None:
        self._user = user

    async def find_by_id(self, user_id):  # type: ignore[no-untyped-def]
        return self._user if self._user and self._user.id == user_id else None

    async def find_by_email(self, email: Email) -> User | None:
        return self._user if self._user and self._user.email == email else None

    async def save(self, user: User) -> None:
        self._user = user


class _FakePasswordHasher:
    def hash(self, plain_password: str) -> HashedPassword:
        return HashedPassword(value=f"hashed::{plain_password}")

    def verify(self, hashed: HashedPassword, plain_password: str) -> bool:
        return hashed.value == f"hashed::{plain_password}"


class _FakeTokenService:
    def issue_access_token(self, user_id, tier: str) -> str:  # type: ignore[no-untyped-def]
        return f"token-{user_id}-{tier}"


def _seed_user() -> User:
    return User(
        id=uuid4(),
        email=Email.create("demo@numen.app"),
        display_name="Demo",
        hashed_password=HashedPassword(value="hashed::demo1234"),
        tier="free",
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_login_returns_token_on_valid_credentials() -> None:
    user = _seed_user()
    use_case = LoginUseCase(
        auth_repository=_InMemoryAuthRepository(user),
        password_hasher=_FakePasswordHasher(),
        token_service=_FakeTokenService(),
    )

    result = await use_case.execute(
        LoginInputDTO(email="demo@numen.app", password="demo1234")
    )

    assert result.email == "demo@numen.app"
    assert result.tier == "free"
    assert result.access_token.startswith("token-")


@pytest.mark.asyncio
async def test_login_rejects_wrong_password() -> None:
    user = _seed_user()
    use_case = LoginUseCase(
        auth_repository=_InMemoryAuthRepository(user),
        password_hasher=_FakePasswordHasher(),
        token_service=_FakeTokenService(),
    )

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(
            LoginInputDTO(email="demo@numen.app", password="wrong")
        )


@pytest.mark.asyncio
async def test_login_rejects_unknown_email() -> None:
    use_case = LoginUseCase(
        auth_repository=_InMemoryAuthRepository(None),
        password_hasher=_FakePasswordHasher(),
        token_service=_FakeTokenService(),
    )

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(
            LoginInputDTO(email="ghost@numen.app", password="whatever")
        )
