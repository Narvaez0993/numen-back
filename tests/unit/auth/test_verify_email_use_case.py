from datetime import timedelta

import pytest

from src.modules.auth.application.dto.verify_email import VerifyEmailInputDTO
from src.modules.auth.application.use_cases.verify_email import VerifyEmailUseCase
from src.modules.auth.domain.entities.email_verification_code import EmailVerificationCode
from src.modules.auth.domain.errors import (
    VerificationAttemptsExceededError,
    VerificationCodeExpiredError,
    VerificationCodeInvalidError,
)
from tests.unit.auth.fakes import (
    FIXED_NOW,
    FixedClock,
    InMemoryAuthRepository,
    InMemoryRefreshTokenRepository,
    InMemoryVerificationCodeRepository,
    make_session_issuer,
    make_user,
)

MAX_ATTEMPTS = 5


def _seed_code(user_id, *, code="123456", attempts=0, ttl_minutes=15):  # type: ignore[no-untyped-def]
    return EmailVerificationCode(
        user_id=user_id,
        code=code,
        expires_at=FIXED_NOW + timedelta(minutes=ttl_minutes),
        attempts=attempts,
        resend_available_at=FIXED_NOW + timedelta(seconds=60),
        created_at=FIXED_NOW,
    )


def _use_case(
    auth_repo: InMemoryAuthRepository,
    codes: InMemoryVerificationCodeRepository,
    clock: FixedClock,
) -> VerifyEmailUseCase:
    return VerifyEmailUseCase(
        auth_repository=auth_repo,
        verification_code_repository=codes,
        session_issuer=make_session_issuer(clock, InMemoryRefreshTokenRepository()),
        clock=clock,
        max_attempts=MAX_ATTEMPTS,
    )


@pytest.mark.asyncio
async def test_verify_marks_user_verified_and_returns_session() -> None:
    user = make_user(verified=False)
    auth_repo = InMemoryAuthRepository(user)
    codes = InMemoryVerificationCodeRepository()
    await codes.save(_seed_code(user.id))

    result = await _use_case(auth_repo, codes, FixedClock()).execute(
        VerifyEmailInputDTO(email="demo@numen.app", code="123456")
    )

    assert result.access_token.startswith("access-")
    assert result.refresh_token != ""
    assert auth_repo.users[0].email_verified is True
    assert await codes.find_active_by_user(user.id) is None


@pytest.mark.asyncio
async def test_verify_rejects_wrong_code_and_counts_attempt() -> None:
    user = make_user(verified=False)
    codes = InMemoryVerificationCodeRepository()
    await codes.save(_seed_code(user.id))

    with pytest.raises(VerificationCodeInvalidError):
        await _use_case(InMemoryAuthRepository(user), codes, FixedClock()).execute(
            VerifyEmailInputDTO(email="demo@numen.app", code="000000")
        )

    stored = await codes.find_active_by_user(user.id)
    assert stored is not None
    assert stored.attempts == 1


@pytest.mark.asyncio
async def test_verify_rejects_expired_code() -> None:
    user = make_user(verified=False)
    codes = InMemoryVerificationCodeRepository()
    await codes.save(_seed_code(user.id))
    clock = FixedClock()
    clock.advance(timedelta(minutes=16))

    with pytest.raises(VerificationCodeExpiredError):
        await _use_case(InMemoryAuthRepository(user), codes, clock).execute(
            VerifyEmailInputDTO(email="demo@numen.app", code="123456")
        )


@pytest.mark.asyncio
async def test_verify_rejects_when_attempts_exhausted() -> None:
    user = make_user(verified=False)
    codes = InMemoryVerificationCodeRepository()
    await codes.save(_seed_code(user.id, attempts=MAX_ATTEMPTS))

    with pytest.raises(VerificationAttemptsExceededError):
        await _use_case(InMemoryAuthRepository(user), codes, FixedClock()).execute(
            VerifyEmailInputDTO(email="demo@numen.app", code="123456")
        )
