from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from src.modules.auth.application.services.session_issuer import SessionIssuer
from src.modules.auth.domain.entities.email_verification_code import EmailVerificationCode
from src.modules.auth.domain.entities.refresh_token import RefreshToken
from src.modules.auth.domain.entities.user import User
from src.modules.auth.domain.value_objects.email import Email
from src.modules.auth.domain.value_objects.hashed_password import HashedPassword
from src.modules.auth.domain.value_objects.preferences import UserPreferences

FIXED_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


class FixedClock:
    def __init__(self, now: datetime = FIXED_NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta


class InMemoryAuthRepository:
    def __init__(self, *users: User) -> None:
        self.users: list[User] = list(users)

    async def find_by_id(self, user_id: UUID) -> User | None:
        return next((u for u in self.users if u.id == user_id), None)

    async def find_by_email(self, email: Email) -> User | None:
        return next((u for u in self.users if u.email == email), None)

    async def save(self, user: User) -> None:
        self.users = [u for u in self.users if u.id != user.id]
        self.users.append(user)


class InMemoryVerificationCodeRepository:
    def __init__(self) -> None:
        self.codes: dict[UUID, EmailVerificationCode] = {}

    async def find_active_by_user(self, user_id: UUID) -> EmailVerificationCode | None:
        return self.codes.get(user_id)

    async def save(self, code: EmailVerificationCode) -> None:
        self.codes[code.user_id] = code

    async def delete_by_user(self, user_id: UUID) -> None:
        self.codes.pop(user_id, None)


class InMemoryRefreshTokenRepository:
    def __init__(self) -> None:
        self.tokens: list[RefreshToken] = []

    async def save(self, token: RefreshToken) -> None:
        self.tokens = [t for t in self.tokens if t.id != token.id]
        self.tokens.append(token)

    async def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        return next((t for t in self.tokens if t.token_hash == token_hash), None)

    async def revoke_family(self, family_id: UUID, revoked_at: datetime) -> None:
        self.tokens = [
            t.revoke(revoked_at) if t.family_id == family_id and t.revoked_at is None else t
            for t in self.tokens
        ]


class FakePasswordHasher:
    def hash(self, plain_password: str) -> HashedPassword:
        return HashedPassword(value=f"hashed::{plain_password}")

    def verify(self, hashed: HashedPassword, plain_password: str) -> bool:
        return hashed.value == f"hashed::{plain_password}"


class FakeTokenService:
    def issue_access_token(self, user_id: UUID, tier: str) -> str:
        return f"access-{user_id}-{tier}"


class FakeCodeGenerator:
    def __init__(self, code: str = "123456") -> None:
        self.code = code

    def generate(self) -> str:
        return self.code


class FakeRefreshTokenIssuer:
    def __init__(self) -> None:
        self._counter = 0

    def issue(self) -> tuple[str, str]:
        self._counter += 1
        raw = f"refresh-{self._counter}"
        return raw, self.hash(raw)

    def hash(self, raw_token: str) -> str:
        return f"h:{raw_token}"


class FakeEmailSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_verification_code(self, email: str, code: str) -> None:
        self.sent.append((email, code))


def make_user(*, verified: bool = False, password: str = "demo1234") -> User:
    return User(
        id=uuid4(),
        email=Email.create("demo@numen.app"),
        display_name="Demo",
        hashed_password=HashedPassword(value=f"hashed::{password}"),
        tier="free",
        email_verified=verified,
        created_at=FIXED_NOW,
        preferences=UserPreferences.default(),
    )


def make_session_issuer(
    clock: FixedClock,
    refresh_repo: InMemoryRefreshTokenRepository,
    refresh_ttl_days: int = 30,
) -> SessionIssuer:
    return SessionIssuer(
        token_service=FakeTokenService(),
        refresh_token_issuer=FakeRefreshTokenIssuer(),
        refresh_token_repository=refresh_repo,
        clock=clock,
        refresh_ttl_days=refresh_ttl_days,
    )
