import pytest

from src.modules.auth.application.dto.register import RegisterInputDTO
from src.modules.auth.application.use_cases.register import RegisterUseCase
from src.modules.auth.domain.entities.user import User
from src.modules.auth.domain.errors import UserAlreadyExistsError, WeakPasswordError
from src.modules.auth.domain.value_objects.email import Email
from src.modules.auth.domain.value_objects.hashed_password import HashedPassword
from tests.unit.auth.test_login_use_case import (
    _FakePasswordHasher,
    _FakeTokenService,
    _InMemoryAuthRepository,
)


@pytest.mark.asyncio
async def test_register_creates_user_and_returns_token() -> None:
    repo = _InMemoryAuthRepository()
    use_case = RegisterUseCase(
        auth_repository=repo,
        password_hasher=_FakePasswordHasher(),
        token_service=_FakeTokenService(),
    )

    result = await use_case.execute(
        RegisterInputDTO(
            email="new@numen.app",
            password="strong-enough",
            display_name="New User",
        )
    )

    assert result.email == "new@numen.app"
    assert result.tier == "free"
    assert result.display_name == "New User"
    assert result.access_token.startswith("token-")


@pytest.mark.asyncio
async def test_register_rejects_weak_password() -> None:
    use_case = RegisterUseCase(
        auth_repository=_InMemoryAuthRepository(),
        password_hasher=_FakePasswordHasher(),
        token_service=_FakeTokenService(),
    )

    with pytest.raises(WeakPasswordError):
        await use_case.execute(
            RegisterInputDTO(
                email="new@numen.app",
                password="short",
                display_name="X",
            )
        )


@pytest.mark.asyncio
async def test_register_rejects_existing_email() -> None:
    seeded = User.new(
        email=Email.create("existing@numen.app"),
        display_name="Existing",
        hashed_password=HashedPassword(value="x"),
    )
    use_case = RegisterUseCase(
        auth_repository=_InMemoryAuthRepository(seeded),
        password_hasher=_FakePasswordHasher(),
        token_service=_FakeTokenService(),
    )

    with pytest.raises(UserAlreadyExistsError):
        await use_case.execute(
            RegisterInputDTO(
                email="existing@numen.app",
                password="another-strong-pw",
                display_name="Other",
            )
        )
