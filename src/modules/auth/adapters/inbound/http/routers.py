from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.modules.auth.adapters.inbound.http.schemas import (
    AuthResponse,
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
)
from src.modules.auth.application.dto.login import LoginInputDTO
from src.modules.auth.application.dto.register import RegisterInputDTO
from src.modules.auth.application.ports.auth_repository import AuthRepository
from src.modules.auth.application.use_cases.login import LoginUseCase
from src.modules.auth.application.use_cases.register import RegisterUseCase
from src.modules.auth.domain.errors import InvalidCredentialsError
from src.shared.adapters.inbound.http.dependencies import get_current_user_id

router = APIRouter(prefix="/auth", tags=["auth"])


def _depends_register_use_case() -> RegisterUseCase:
    from src.core.di.container import get_container

    return get_container().register_use_case


def _depends_login_use_case() -> LoginUseCase:
    from src.core.di.container import get_container

    return get_container().login_use_case


def _depends_auth_repository() -> AuthRepository:
    from src.core.di.container import get_container

    return get_container().auth_repository


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=AuthResponse)
async def register(
    body: RegisterRequest,
    use_case: RegisterUseCase = Depends(_depends_register_use_case),
) -> AuthResponse:
    output = await use_case.execute(
        RegisterInputDTO(
            email=body.email,
            password=body.password,
            display_name=body.display_name,
        )
    )
    return AuthResponse(**output.model_dump())


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    use_case: LoginUseCase = Depends(_depends_login_use_case),
) -> AuthResponse:
    output = await use_case.execute(
        LoginInputDTO(email=body.email, password=body.password)
    )
    return AuthResponse(**output.model_dump())


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
    )
