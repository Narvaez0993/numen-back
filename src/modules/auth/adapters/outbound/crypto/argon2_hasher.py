from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2.exceptions import VerifyMismatchError

from src.modules.auth.domain.value_objects.hashed_password import HashedPassword


class Argon2Hasher:
    """`PasswordHasher` implementation backed by argon2-cffi."""

    def __init__(self) -> None:
        self._hasher = Argon2PasswordHasher()

    def hash(self, plain_password: str) -> HashedPassword:
        return HashedPassword(value=self._hasher.hash(plain_password))

    def verify(self, hashed: HashedPassword, plain_password: str) -> bool:
        try:
            return self._hasher.verify(hashed.value, plain_password)
        except VerifyMismatchError:
            return False
