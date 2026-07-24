from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.modules.auth.adapters.inbound.http.schemas import (
    AuthResponse,
    CurrentUserResponse,
    LoginRequest,
    LogoutRequest,
    PendingVerificationResponse,
    RefreshRequest,
    RegisterRequest,
    ResendCodeRequest,
    VerifyEmailRequest,
)
from src.modules.auth.application.dto.login import LoginInputDTO
from src.modules.auth.application.dto.register import RegisterInputDTO
from src.modules.auth.application.dto.resend_code import ResendCodeInputDTO
from src.modules.auth.application.dto.token import LogoutInputDTO, RefreshInputDTO
from src.modules.auth.application.dto.verify_email import VerifyEmailInputDTO
from src.modules.auth.application.ports.auth_repository import AuthRepository
from src.modules.auth.application.use_cases.login import LoginUseCase
from src.modules.auth.application.use_cases.logout import LogoutUseCase
from src.modules.auth.application.use_cases.refresh import RefreshUseCase
from src.modules.auth.application.use_cases.register import RegisterUseCase
from src.modules.auth.application.use_cases.resend_code import ResendCodeUseCase
from src.modules.auth.application.use_cases.verify_email import VerifyEmailUseCase
from src.modules.auth.domain.errors import InvalidCredentialsError
from src.shared.adapters.inbound.http.dependencies import get_current_user_id

router = APIRouter(prefix="/auth", tags=["auth"])


def _depends_register_use_case() -> RegisterUseCase:
    from src.core.di.container import get_container

    return get_container().register_use_case


def _depends_login_use_case() -> LoginUseCase:
    from src.core.di.container import get_container

    return get_container().login_use_case


def _depends_verify_email_use_case() -> VerifyEmailUseCase:
    from src.core.di.container import get_container

    return get_container().verify_email_use_case


def _depends_resend_code_use_case() -> ResendCodeUseCase:
    from src.core.di.container import get_container

    return get_container().resend_code_use_case


def _depends_refresh_use_case() -> RefreshUseCase:
    from src.core.di.container import get_container

    return get_container().refresh_use_case


def _depends_logout_use_case() -> LogoutUseCase:
    from src.core.di.container import get_container

    return get_container().logout_use_case


def _depends_auth_repository() -> AuthRepository:
    from src.core.di.container import get_container

    return get_container().auth_repository


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=PendingVerificationResponse,
)
async def register(
    body: RegisterRequest,
    use_case: RegisterUseCase = Depends(_depends_register_use_case),
) -> PendingVerificationResponse:
    output = await use_case.execute(
        RegisterInputDTO(
            email=body.email,
            password=body.password,
            display_name=body.display_name,
        )
    )
    return PendingVerificationResponse(**output.model_dump())


@router.post("/verify-email", response_model=AuthResponse)
async def verify_email(
    body: VerifyEmailRequest,
    use_case: VerifyEmailUseCase = Depends(_depends_verify_email_use_case),
) -> AuthResponse:
    output = await use_case.execute(
        VerifyEmailInputDTO(email=body.email, code=body.code)
    )
    return AuthResponse(**output.model_dump())


@router.post("/resend-code", status_code=status.HTTP_202_ACCEPTED)
async def resend_code(
    body: ResendCodeRequest,
    use_case: ResendCodeUseCase = Depends(_depends_resend_code_use_case),
) -> dict[str, str]:
    await use_case.execute(ResendCodeInputDTO(email=body.email))
    return {"status": "sent"}


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    use_case: LoginUseCase = Depends(_depends_login_use_case),
) -> AuthResponse:
    output = await use_case.execute(
        LoginInputDTO(email=body.email, password=body.password)
    )
    return AuthResponse(**output.model_dump())


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    body: RefreshRequest,
    use_case: RefreshUseCase = Depends(_depends_refresh_use_case),
) -> AuthResponse:
    output = await use_case.execute(RefreshInputDTO(refresh_token=body.refresh_token))
    return AuthResponse(**output.model_dump())


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    use_case: LogoutUseCase = Depends(_depends_logout_use_case),
) -> None:
    await use_case.execute(LogoutInputDTO(refresh_token=body.refresh_token))


@router.get("/me", response_model=CurrentUserResponse)
async def me(
    user_id: UUID = Depends(get_current_user_id),
    repository: AuthRepository = Depends(_depends_auth_repository),
) -> CurrentUserResponse:
    user = await repository.find_by_id(user_id)
    if user is None:
        raise InvalidCredentialsError()
    return CurrentUserResponse(
        user_id=str(user.id),
        email=user.email.value,
        display_name=user.display_name,
        tier=user.tier,
        email_verified=user.email_verified,
    )
