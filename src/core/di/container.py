from dataclasses import dataclass
from functools import lru_cache

from src.modules.auth.adapters.outbound.crypto.argon2_hasher import Argon2Hasher
from src.modules.auth.adapters.outbound.crypto.jwt_token_service import JwtTokenService
from src.modules.auth.adapters.outbound.crypto.secrets_code_generator import (
    SecretsCodeGenerator,
)
from src.modules.auth.adapters.outbound.crypto.secrets_refresh_token_issuer import (
    SecretsRefreshTokenIssuer,
)
from src.modules.auth.adapters.outbound.email.logging_email_sender import LoggingEmailSender
from src.modules.auth.adapters.outbound.persistence.repositories.mongo_auth_repository import (
    MongoAuthRepository,
)
from src.modules.auth.adapters.outbound.persistence.repositories.mongo_refresh_token_repository import (  # noqa: E501
    MongoRefreshTokenRepository,
)
from src.modules.auth.adapters.outbound.persistence.repositories.mongo_verification_code_repository import (  # noqa: E501
    MongoVerificationCodeRepository,
)
from src.modules.auth.application.ports.auth_repository import AuthRepository
from src.modules.auth.application.ports.code_generator import CodeGenerator
from src.modules.auth.application.ports.email_sender import EmailSender
from src.modules.auth.application.ports.password_hasher import PasswordHasher
from src.modules.auth.application.ports.refresh_token_issuer import RefreshTokenIssuer
from src.modules.auth.application.ports.refresh_token_repository import RefreshTokenRepository
from src.modules.auth.application.ports.token_service import TokenService
from src.modules.auth.application.ports.verification_code_repository import (
    VerificationCodeRepository,
)
from src.modules.auth.application.services.session_issuer import SessionIssuer
from src.modules.auth.application.use_cases.login import LoginUseCase
from src.modules.auth.application.use_cases.logout import LogoutUseCase
from src.modules.auth.application.use_cases.refresh import RefreshUseCase
from src.modules.auth.application.use_cases.register import RegisterUseCase
from src.modules.auth.application.use_cases.resend_code import ResendCodeUseCase
from src.modules.auth.application.use_cases.update_display_name import (
    UpdateDisplayNameUseCase,
)
from src.modules.auth.application.use_cases.verify_email import VerifyEmailUseCase
from src.shared.adapters.outbound.config.settings import Settings, get_settings
from src.shared.adapters.outbound.time.system_clock import SystemClock
from src.shared.application.ports.clock import Clock


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
    clock: Clock
    verification_code_repository: VerificationCodeRepository
    refresh_token_repository: RefreshTokenRepository
    code_generator: CodeGenerator
    refresh_token_issuer: RefreshTokenIssuer
    email_sender: EmailSender

    # Use cases (inbound ports)
    login_use_case: LoginUseCase
    register_use_case: RegisterUseCase
    verify_email_use_case: VerifyEmailUseCase
    resend_code_use_case: ResendCodeUseCase
    refresh_use_case: RefreshUseCase
    logout_use_case: LogoutUseCase
    update_display_name_use_case: UpdateDisplayNameUseCase


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()

    auth_repository: AuthRepository = MongoAuthRepository()
    password_hasher: PasswordHasher = Argon2Hasher()
    token_service: TokenService = JwtTokenService(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        access_ttl_minutes=settings.jwt_access_ttl_minutes,
    )
    clock: Clock = SystemClock()
    verification_code_repository: VerificationCodeRepository = (
        MongoVerificationCodeRepository()
    )
    refresh_token_repository: RefreshTokenRepository = MongoRefreshTokenRepository()
    code_generator: CodeGenerator = SecretsCodeGenerator(
        length=settings.verification_code_length
    )
    refresh_token_issuer: RefreshTokenIssuer = SecretsRefreshTokenIssuer()
    email_sender: EmailSender = LoggingEmailSender()

    session_issuer = SessionIssuer(
        token_service=token_service,
        refresh_token_issuer=refresh_token_issuer,
        refresh_token_repository=refresh_token_repository,
        clock=clock,
        refresh_ttl_days=settings.jwt_refresh_ttl_days,
    )

    return Container(
        settings=settings,
        auth_repository=auth_repository,
        password_hasher=password_hasher,
        token_service=token_service,
        clock=clock,
        verification_code_repository=verification_code_repository,
        refresh_token_repository=refresh_token_repository,
        code_generator=code_generator,
        refresh_token_issuer=refresh_token_issuer,
        email_sender=email_sender,
        login_use_case=LoginUseCase(
            auth_repository=auth_repository,
            password_hasher=password_hasher,
            session_issuer=session_issuer,
        ),
        register_use_case=RegisterUseCase(
            auth_repository=auth_repository,
            password_hasher=password_hasher,
            code_generator=code_generator,
            verification_code_repository=verification_code_repository,
            email_sender=email_sender,
            clock=clock,
            code_ttl_minutes=settings.verification_code_ttl_minutes,
            resend_cooldown_seconds=settings.verification_resend_cooldown_seconds,
        ),
        verify_email_use_case=VerifyEmailUseCase(
            auth_repository=auth_repository,
            verification_code_repository=verification_code_repository,
            session_issuer=session_issuer,
            clock=clock,
            max_attempts=settings.verification_max_attempts,
        ),
        resend_code_use_case=ResendCodeUseCase(
            auth_repository=auth_repository,
            verification_code_repository=verification_code_repository,
            code_generator=code_generator,
            email_sender=email_sender,
            clock=clock,
            code_ttl_minutes=settings.verification_code_ttl_minutes,
            resend_cooldown_seconds=settings.verification_resend_cooldown_seconds,
        ),
        refresh_use_case=RefreshUseCase(
            auth_repository=auth_repository,
            refresh_token_repository=refresh_token_repository,
            refresh_token_issuer=refresh_token_issuer,
            session_issuer=session_issuer,
            clock=clock,
        ),
        logout_use_case=LogoutUseCase(
            refresh_token_repository=refresh_token_repository,
            refresh_token_issuer=refresh_token_issuer,
            clock=clock,
        ),
        update_display_name_use_case=UpdateDisplayNameUseCase(
            auth_repository=auth_repository,
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
