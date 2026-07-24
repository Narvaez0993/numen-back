from typing import Protocol

from src.modules.auth.domain.value_objects.hashed_password import HashedPassword


class PasswordHasher(Protocol):
    """Outbound port: opaque password hashing."""

    def hash(self, plain_password: str) -> HashedPassword: ...

    def verify(self, hashed: HashedPassword, plain_password: str) -> bool: ...
