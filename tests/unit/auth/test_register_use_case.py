import pytest

from src.modules.auth.application.dto.register import RegisterInputDTO
from src.modules.auth.application.use_cases.register import RegisterUseCase
from src.modules.auth.domain.errors import UserAlreadyExistsError, WeakPasswordError
from tests.unit.auth.fakes import (
    FakeCodeGenerator,
    FakeEmailSender,
    FakePasswordHasher,
    FixedClock,
    InMemoryAuthRepository,
    InMemoryVerificationCodeRepository,
    make_user,
)


def _use_case(
    repo: InMemoryAuthRepository,
    codes: InMemoryVerificationCodeRepository,
    email_sender: FakeEmailSender,
) -> RegisterUseCase:
    return RegisterUseCase(
        auth_repository=repo,
        password_hasher=FakePasswordHasher(),
        code_generator=FakeCodeGenerator("123456"),
        verification_code_repository=codes,
        email_sender=email_sender,
        clock=FixedClock(),
        code_ttl_minutes=15,
        resend_cooldown_seconds=60,
    )


@pytest.mark.asyncio
async def test_register_creates_unverified_user_and_sends_code() -> None:
    repo = InMemoryAuthRepository()
    codes = InMemoryVerificationCodeRepository()
    email_sender = FakeEmailSender()

    result = await _use_case(repo, codes, email_sender).execute(
        RegisterInputDTO(
            email="new@numen.app",
            password="strong-enough",
            display_name="New User",
        )
    )

    assert result.email == "new@numen.app"
    assert result.email_verified is False
    assert len(repo.users) == 1
    assert repo.users[0].email_verified is False
    assert email_sender.sent == [("new@numen.app", "123456")]


@pytest.mark.asyncio
async def test_register_rejects_weak_password() -> None:
    use_case = _use_case(
        InMemoryAuthRepository(),
        InMemoryVerificationCodeRepository(),
        FakeEmailSender(),
    )

    with pytest.raises(WeakPasswordError):
        await use_case.execute(
            RegisterInputDTO(email="new@numen.app", password="short", display_name="X")
        )


@pytest.mark.asyncio
async def test_register_rejects_existing_email() -> None:
    use_case = _use_case(
        InMemoryAuthRepository(make_user()),
        InMemoryVerificationCodeRepository(),
        FakeEmailSender(),
    )

    with pytest.raises(UserAlreadyExistsError):
        await use_case.execute(
            RegisterInputDTO(
                email="demo@numen.app", password="strong-enough", display_name="Dup"
            )
        )
