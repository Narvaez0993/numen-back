from dataclasses import dataclass
from functools import lru_cache

from src.modules.auth.adapters.outbound.crypto.argon2_hasher import Argon2Hasher
from src.modules.auth.adapters.outbound.crypto.jwt_token_service import JwtTokenService
from src.modules.auth.adapters.outbound.persistence.repositories.mongo_auth_repository import (
    MongoAuthRepository,
)
from src.modules.auth.application.ports.auth_repository import AuthRepository
from src.modules.auth.application.ports.password_hasher import PasswordHasher
from src.modules.auth.application.ports.token_service import TokenService
from src.modules.auth.application.use_cases.login import LoginUseCase
from src.modules.auth.application.use_cases.register import RegisterUseCase
from src.shared.adapters.outbound.config.settings import Settings, get_settings


@dataclass
class Container:
    """Composition root: instantiates ports' implementations and use cases.

    Routers (adapters/inbound/http) pull from here via FastAPI Depends. Workers
    pull from here on startup. Tests can replace specific fields with fakes.
    """

    settings: Settings

    # Ports → outbound adapters
    auth_repository: AuthRepository
    password_hasher: PasswordHasher
    token_service: TokenService

    # Use cases (inbound ports)
    login_use_case: LoginUseCase
    register_use_case: RegisterUseCase


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()

    auth_repository: AuthRepository = MongoAuthRepository()
    password_hasher: PasswordHasher = Argon2Hasher()
    token_service: TokenService = JwtTokenService(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        access_ttl_minutes=settings.jwt_access_ttl_minutes,
    )

    return Container(
        settings=settings,
        auth_repository=auth_repository,
        password_hasher=password_hasher,
        token_service=token_service,
        login_use_case=LoginUseCase(
            auth_repository=auth_repository,
            password_hasher=password_hasher,
            token_service=token_service,
        ),
        register_use_case=RegisterUseCase(
            auth_repository=auth_repository,
            password_hasher=password_hasher,
            token_service=token_service,
        ),
    )


@lru_cache
def get_container() -> Container:
    return build_container()


def reset_container() -> None:
    """For tests: clear the cached container so the next call rebuilds it.

    To inject test doubles, build a fresh container and set it via FastAPI's
    `app.dependency_overrides[get_container] = lambda: my_container`.
    """
    get_container.cache_clear()
