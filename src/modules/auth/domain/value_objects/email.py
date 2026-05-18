import re
from dataclasses import dataclass
from typing import ClassVar

from src.shared.domain.errors import ValidationError

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class InvalidEmailError(ValidationError):
    code: ClassVar[str] = "auth.invalid_email"


@dataclass(frozen=True)
class Email:
    value: str

    @classmethod
    def create(cls, raw: str) -> "Email":
        trimmed = raw.strip().lower()
        if not _EMAIL_RE.match(trimmed):
            raise InvalidEmailError(f"Invalid email: {raw}")
        return cls(value=trimmed)

    def __str__(self) -> str:
        return self.value
