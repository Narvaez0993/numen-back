from dataclasses import dataclass


@dataclass(frozen=True)
class HashedPassword:
    """Opaque hash produced by a `PasswordHasher`. Never compared in domain."""

    value: str
