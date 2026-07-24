from datetime import timedelta

import pytest

from src.modules.auth.application.dto.resend_code import ResendCodeInputDTO
from src.modules.auth.application.use_cases.resend_code import ResendCodeUseCase
from src.modules.auth.domain.entities.email_verification_code import EmailVerificationCode
from src.modules.auth.domain.errors import ResendCooldownError, VerificationCodeInvalidError
from tests.unit.auth.fakes import (
    FakeCodeGenerator,
    FakeEmailSender,
    FixedClock,
    InMemoryAuthRepository,
    InMemoryVerificationCodeRepository,
    make_user,
)


def _use_case(
    auth_repo: InMemoryAuthRepository,
    codes: InMemoryVerificationCodeRepository,
    email_sender: FakeEmailSender,
    clock: FixedClock,
) -> ResendCodeUseCase:
    return ResendCodeUseCase(
        auth_repository=auth_repo,
        verification_code_repository=codes,
        code_generator=FakeCodeGenerator("654321"),
        email_sender=email_sender,
        clock=clock,
        code_ttl_minutes=15,
        resend_cooldown_seconds=60,
    )


@pytest.mark.asyncio
async def test_resend_within_cooldown_is_rejected() -> None:
    user = make_user(verified=False)
    codes = InMemoryVerificationCodeRepository()
    email_sender = FakeEmailSender()
    clock = FixedClock()
    await codes.save(
        EmailVerificationCode(
            user_id=user.id,
            code="123456",
            expires_at=clock.now() + timedelta(minutes=15),
            attempts=0,
            resend_available_at=clock.now() + timedelta(seconds=60),
            created_at=clock.now(),
        )
    )

    with pytest.raises(ResendCooldownError):
        await _use_case(
            InMemoryAuthRepository(user), codes, email_sender, clock
        ).execute(ResendCodeInputDTO(email="demo@numen.app"))


@pytest.mark.asyncio
async def test_resend_after_cooldown_issues_new_code() -> None:
    user = make_user(verified=False)
    codes = InMemoryVerificationCodeRepository()
    email_sender = FakeEmailSender()
    clock = FixedClock()

    await codes.save(
        EmailVerificationCode(
            user_id=user.id,
            code="123456",
            expires_at=clock.now() + timedelta(minutes=15),
            attempts=3,
            resend_available_at=clock.now() + timedelta(seconds=60),
            created_at=clock.now(),
        )
    )
    clock.advance(timedelta(seconds=61))

    await _use_case(InMemoryAuthRepository(user), codes, email_sender, clock).execute(
        ResendCodeInputDTO(email="demo@numen.app")
    )

    stored = await codes.find_active_by_user(user.id)
    assert stored is not None
    assert stored.code == "654321"
    assert stored.attempts == 0
    assert email_sender.sent == [("demo@numen.app", "654321")]


@pytest.mark.asyncio
async def test_resend_for_verified_user_is_rejected() -> None:
    user = make_user(verified=True)

    with pytest.raises(VerificationCodeInvalidError):
        await _use_case(
            InMemoryAuthRepository(user),
            InMemoryVerificationCodeRepository(),
            FakeEmailSender(),
            FixedClock(),
        ).execute(ResendCodeInputDTO(email="demo@numen.app"))
